import asyncio
import json
from collections.abc import AsyncIterator

from app.config import Settings
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas import AnalyzeTicketRequest, TicketAnalysisResponse, RetrievedCase
from app.services.model_service import DashscopeService
from app.services.retrieval_service import ChromaKnowledgeService


class TicketService:
    def __init__(self, settings: Settings, repository: SqliteRepository, knowledge: ChromaKnowledgeService, model: DashscopeService):
        self.repository = repository
        self.knowledge = knowledge
        self.model = model

    @staticmethod
    def _prompts(request: AnalyzeTicketRequest, context: str) -> tuple[str, str]:
        system_prompt = """
你是日本游戏客服辅助系统。你只能依据用户消息、检索资料和规则生成结构化结果。
禁止编造退款、补偿、处理时限、账号恢复或后台操作结果。
如果资料不足，必须在 missing_information 中说明，并将风险提高。
只返回 JSON，字段必须为：intent、risk_level、missing_information、chinese_guidance、japanese_reply、quality_warnings。
risk_level 只能是 low、medium、high。
""".strip()
        user_prompt = f"用户消息：\n{request.message}\n\n检索资料：\n{context or '没有检索到可靠资料'}"
        return system_prompt, user_prompt

    @staticmethod
    def _query(request: AnalyzeTicketRequest) -> str:
        return "\n".join(
            part for part in [
                request.message,
                f"平台：{request.platform}" if request.platform else "",
                f"应用版本：{request.app_version}" if request.app_version else "",
            ] if part
        )

    def _response(self, request: AnalyzeTicketRequest, result: dict, retrieved: list[dict]) -> TicketAnalysisResponse:
        response = TicketAnalysisResponse(
            intent=result.get("intent", "未分类"),
            risk_level=result.get("risk_level", "high"),
            missing_information=result.get("missing_information", []),
            chinese_guidance=result.get("chinese_guidance", ""),
            japanese_reply=result.get("japanese_reply", ""),
            quality_warnings=result.get("quality_warnings", []),
            retrieved_cases=[RetrievedCase(**{key: item.get(key) for key in ("case_id", "distance", "rerank_score", "document", "metadata")}) for item in retrieved],
        )
        if request.thread_id:
            self.repository.save_summary(
                request.thread_id,
                {"latest_message": request.message, "intent": response.intent, "risk_level": response.risk_level},
            )
        return response

    async def analyze(self, request: AnalyzeTicketRequest) -> TicketAnalysisResponse:
        query = self._query(request)
        retrieved = self.knowledge.search(query)
        context = "\n\n".join(
            f"来源：{item['collection']}\n{item['document']}" for item in retrieved
        )
        system_prompt, user_prompt = self._prompts(request, context)
        result = await self.model.generate_json(system_prompt, user_prompt)
        return self._response(request, result, retrieved)

    async def analyze_stream(self, request: AnalyzeTicketRequest) -> AsyncIterator[dict]:
        yield {"event": "stage", "data": {"stage": "received", "message": "已接收玩家来信"}}
        query = self._query(request)
        yield {"event": "stage", "data": {"stage": "retrieving", "message": "正在检索相似案例与客服知识"}}
        retrieved = await asyncio.to_thread(self.knowledge.search, query)
        context = "\n\n".join(f"来源：{item['collection']}\n{item['document']}" for item in retrieved)
        system_prompt, user_prompt = self._prompts(request, context)
        yield {"event": "stage", "data": {"stage": "generating", "message": "正在生成中文建议与日语回复"}}
        fragments: list[str] = []
        async for fragment in self.model.generate_json_stream(system_prompt, user_prompt):
            fragments.append(fragment)
            yield {"event": "token", "data": {"content": fragment, "count": len(fragments)}}
        result = json.loads("".join(fragments))
        yield {"event": "stage", "data": {"stage": "validating", "message": "正在执行格式与风险校验"}}
        response = self._response(request, result, retrieved)
        yield {"event": "result", "data": response.model_dump()}
        yield {"event": "done", "data": {"status": "completed"}}
