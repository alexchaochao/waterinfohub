import json
from pathlib import Path
from typing import Optional

import httpx

from waterinfohub.core.settings import settings


class LLMClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self._client = httpx.Client(timeout=30)

    def run_completion(self, prompt: str, temperature: float = 0.2, max_tokens: int = 512) -> str:
        url = f"{self.base_url}/chat/completions" if "/v1" in self.base_url else f"{self.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = self._client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            # Return an empty string and let the caller handle fallback behavior.
            return ""


def load_prompt(prompt_path: Path) -> str:
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()
