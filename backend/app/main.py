from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas import AnalyzeTicketRequest, IngestResponse, KnowledgeStatsResponse, TicketAnalysisResponse
from app.services.ingestion_service import ingest_workbook
from app.services.model_service import DashscopeService
from app.services.retrieval_service import ChromaKnowledgeService
from app.services.ticket_service import TicketService


settings = get_settings()
repository = SqliteRepository(settings.database_path)
knowledge = ChromaKnowledgeService(settings)
model = DashscopeService(settings)
ticket_service = TicketService(settings, repository, knowledge, model)

app = FastAPI(title=settings.project_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}


@app.get("/api/knowledge/stats", response_model=KnowledgeStatsResponse)
def knowledge_stats() -> KnowledgeStatsResponse:
    stats = knowledge.stats()
    return KnowledgeStatsResponse(**stats, indexed_source=settings.source_xlsx_path)


@app.post("/api/knowledge/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    try:
        return IngestResponse(**ingest_workbook(settings, repository, knowledge))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion failed: {error}") from error


@app.post("/api/tickets/analyze", response_model=TicketAnalysisResponse)
async def analyze_ticket(request: AnalyzeTicketRequest) -> TicketAnalysisResponse:
    try:
        return await ticket_service.analyze(request)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Ticket analysis failed: {error}") from error
