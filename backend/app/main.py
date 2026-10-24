import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

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


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/tickets/analyze/stream")
async def analyze_ticket_stream(request: AnalyzeTicketRequest) -> StreamingResponse:
    async def event_generator():
        try:
            async for item in ticket_service.analyze_stream(request):
                yield format_sse(item["event"], item["data"])
        except Exception as error:
            yield format_sse("error", {"message": f"Ticket analysis failed: {error}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
