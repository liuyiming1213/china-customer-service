import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from app.config import get_settings
from app.repositories.sqlite_repository import SqliteRepository
from app.services.ingestion_service import ingest_workbook
from app.services.retrieval_service import ChromaKnowledgeService


def main() -> None:
    settings = get_settings()
    repository = SqliteRepository(settings.database_path)
    knowledge = ChromaKnowledgeService(settings)
    result = ingest_workbook(settings, repository, knowledge)
    print(result)


if __name__ == "__main__":
    main()
