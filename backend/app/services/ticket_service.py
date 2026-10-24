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

    async def analyze(self, request: AnalyzeTicketRequest) -> TicketAnalysisResponse:
        query = "\n".join(
            part for part in [
                request.message,
                f"平台：{request.platform}" if request.platform else "",
                f"应用版本：{request.app_version}" if request.app_version else "",
            ] if part
        )
        retrieved = self.knowledge.search(query)
        context = "\n\n".join(
            f"来源：{item['collection']}\n{item['document']}" for item in retrieved
        )
        system_prompt = """
你是日本游戏客服辅助系统。你只能依据用户消息、检索资料和规则生成结构化结果。
禁止编造退款、补偿、处理时限、账号恢复或后台操作结果。
如果资料不足，必须在 missing_information 中说明，并将风险提高。
只返回 JSON，字段必须为：intent、risk_level、missing_information、chinese_guidance、japanese_reply、quality_warnings。
risk_level 只能是 low、medium、high。
""".strip()
        user_prompt = f"用户消息：\n{request.message}\n\n检索资料：\n{context or '没有检索到可靠资料'}"
        result = await self.model.generate_json(system_prompt, user_prompt)
        if request.thread_id:
            self.repository.save_summary(
                request.thread_id,
                {"latest_message": request.message, "intent": result.get("intent", ""), "risk_level": result.get("risk_level", "high")},
            )
        return TicketAnalysisResponse(
            intent=result.get("intent", "未分类"),
            risk_level=result.get("risk_level", "high"),
            missing_information=result.get("missing_information", []),
            chinese_guidance=result.get("chinese_guidance", ""),
            japanese_reply=result.get("japanese_reply", ""),
            quality_warnings=result.get("quality_warnings", []),
            retrieved_cases=[RetrievedCase(**{key: item.get(key) for key in ("case_id", "distance", "rerank_score", "document", "metadata")}) for item in retrieved],
        )
