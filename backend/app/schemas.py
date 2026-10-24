from typing import Any

from pydantic import BaseModel, Field


class AnalyzeTicketRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str | None = None
    platform: str | None = None
    app_version: str | None = None


class RetrievedCase(BaseModel):
    case_id: str
    distance: float | None = None
    rerank_score: float | None = None
    document: str
    metadata: dict[str, Any] = {}


class TicketAnalysisResponse(BaseModel):
    intent: str
    risk_level: str
    missing_information: list[str]
    chinese_guidance: str
    japanese_reply: str
    quality_warnings: list[str]
    retrieved_cases: list[RetrievedCase]


class IngestResponse(BaseModel):
    imported_threads: int
    imported_messages: int
    indexed_cases: int
    skipped_rows: int


class KnowledgeStatsResponse(BaseModel):
    support_cases: int
    policies: int
    terminology: int
    indexed_source: str
