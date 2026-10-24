import os
from pathlib import Path
from typing import Any

from app.config import Settings


class LocalEmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def _get_model(self):
        if self._model is None:
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            import torch
            from sentence_transformers import SentenceTransformer

            torch.set_num_threads(1)
            self._model = SentenceTransformer(
                self.settings.embedding_model,
                cache_folder=str(Path("backend/models")),
            )
            self._model.max_seq_length = 256
        return self._model

    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        model = self._get_model()
        if "multilingual-e5" in self.settings.embedding_model.lower():
            texts = [f"{kind}: {text}" for text in texts]
        return model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 8,
        ).tolist()


class BgeRerankerService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def _get_model(self):
        if self._model is None:
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            import torch
            from sentence_transformers import CrossEncoder

            torch.set_num_threads(1)
            self._model = CrossEncoder(
                self.settings.reranker_model,
                cache_dir=str(Path("backend/models")),
            )
        return self._model

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        model = self._get_model()
        return [float(score) for score in model.predict([(query, document) for document in documents])]


class ChromaKnowledgeService:
    COLLECTIONS = ("support_cases", "policies", "terminology")

    def __init__(self, settings: Settings):
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.settings = settings
        self.client = chromadb.PersistentClient(
            path=str(Path(settings.chroma_path)),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embedding_service = LocalEmbeddingService(settings)
        self.reranker = BgeRerankerService(settings)
        self.collections = {
            name: self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
            for name in self.COLLECTIONS
        }

    def stats(self) -> dict[str, int]:
        return {name: collection.count() for name, collection in self.collections.items()}

    def add_documents(self, collection_name: str, documents: list[str], metadatas: list[dict[str, Any]], ids: list[str]) -> int:
        if not documents:
            return 0
        embeddings = self.embedding_service.embed(documents, kind="passage")
        self.collections[collection_name].upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(documents)

    def search(self, query: str, n_results: int = 8) -> list[dict[str, Any]]:
        query_embedding = self.embedding_service.embed([query], kind="query")[0]
        candidates: list[dict[str, Any]] = []
        for collection_name, collection in self.collections.items():
            if collection.count() == 0:
                continue
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            for index, document in enumerate(result.get("documents", [[]])[0]):
                candidates.append(
                    {
                        "case_id": result["ids"][0][index],
                        "document": document,
                        "metadata": result.get("metadatas", [[]])[0][index] or {},
                        "distance": result.get("distances", [[]])[0][index],
                        "collection": collection_name,
                    }
                )
        unique_candidates = {candidate["case_id"]: candidate for candidate in candidates}.values()
        candidates = list(unique_candidates)
        if self.settings.enable_reranker and candidates:
            try:
                scores = self.reranker.rerank(query, [candidate["document"] for candidate in candidates])
                for candidate, score in zip(candidates, scores):
                    candidate["rerank_score"] = score
            except Exception:
                for candidate in candidates:
                    candidate["rerank_score"] = 0.0
        return sorted(candidates, key=lambda candidate: candidate.get("rerank_score", 0), reverse=True)[:5]
