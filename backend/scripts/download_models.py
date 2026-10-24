from pathlib import Path

from sentence_transformers import CrossEncoder, SentenceTransformer

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    model_dir = Path("backend/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading embedding model: {settings.embedding_model}")
    SentenceTransformer(settings.embedding_model, cache_folder=str(model_dir))
    print(f"Downloading reranker model: {settings.reranker_model}")
    CrossEncoder(settings.reranker_model, cache_dir=str(model_dir))
    print("Local models are ready.")


if __name__ == "__main__":
    main()
