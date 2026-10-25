import json
from typing import Any, AsyncIterator

import httpx

from app.config import Settings


class DashscopeService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _ensure_key(self) -> None:
        if not self.settings.dashscope_api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")

    @staticmethod
    def _extract_message_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("DashScope returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        if not isinstance(content, str):
            raise RuntimeError("DashScope returned an invalid message content")
        return content

    @staticmethod
    def _extract_stream_content(payload: dict[str, Any]) -> str:
        """Return content from a chunk and safely ignore keep-alive/empty chunks."""
        choices = payload.get("choices") or []
        if not choices:
            return ""
        delta = (choices[0] or {}).get("delta") or {}
        content = delta.get("content") or ""
        return content if isinstance(content, str) else ""

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
        content = self._extract_message_content(response.json())
        return json.loads(content)

    async def generate_json_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        """Yield model output fragments while retaining JSON parsing at the service boundary."""
        self._ensure_key()
        payload = {
            "model": self.settings.dashscope_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.settings.dashscope_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    content = self._extract_stream_content(chunk)
                    if content:
                        yield content
