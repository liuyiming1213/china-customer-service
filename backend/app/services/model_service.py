import json
from typing import Any

import httpx

from app.config import Settings


class DashscopeService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _ensure_key(self) -> None:
        if not self.settings.dashscope_api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._ensure_key()
        payload = {
            "model": self.settings.dashscope_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.settings.dashscope_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
