"""Cliente mínimo para qualquer endpoint OpenAI-compatível (Ollama, vLLM, SGLang, gateways de cloud)."""

from __future__ import annotations

import json
import os

import httpx


class ChatClient:
    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 600,
                 reasoning: bool = True):
        self.model = model
        self.reasoning = reasoning  # False: modelo sem modo "thinking" (não manda reasoning_effort)
        headers = {"Authorization": f"Bearer {api_key or os.getenv('LLM_API_KEY', 'none')}"}
        self.http = httpx.AsyncClient(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout)

    async def json_chat(self, messages: list[dict], temperature: float = 0.9, max_tokens: int = 4096) -> tuple[dict, dict]:
        """Retorna (objeto JSON da resposta, usage)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.reasoning:
            payload["reasoning_effort"] = "none"  # desliga o modo "thinking" em modelos Qwen3+
        resp = await self.http.post("/chat/completions", json=payload)
        resp.raise_for_status()
        body = resp.json()
        content = body["choices"][0]["message"]["content"]
        return json.loads(content), body.get("usage", {})

    async def aclose(self) -> None:
        await self.http.aclose()
