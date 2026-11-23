"""OpenAI adapter for the vendor-neutral ModelProvider contract."""

from __future__ import annotations

import json
import os

from .base import ModelRequest, ModelResponse, ProviderError


class OpenAIProvider:
    def __init__(self, model: str | None = None, client=None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self._client = client

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI()
        return self._client

    def generate(self, request: ModelRequest) -> ModelResponse:
        options = {}
        if request.metadata.get("json"):
            options["text"] = {"format": {"type": "json_object"}}
        try:
            response = self._get_client().responses.create(
                model=self.model,
                instructions=request.system_prompt,
                input=list(request.messages),
                **options,
            )
        except Exception as error:  # vendor exceptions never cross this boundary
            raise ProviderError(f"OpenAI request failed: {str(error)[:200]}") from error
        text = (response.output_text or "").strip()
        if not text:
            raise ProviderError("OpenAI returned no text")
        structured = None
        if request.metadata.get("json"):
            try:
                parsed = json.loads(text)
                structured = parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                structured = None
        usage = getattr(response, "usage", None)
        return ModelResponse(
            text=text,
            structured_output=structured,
            usage={
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            },
            provider_metadata={"provider": "openai", "model": self.model},
        )
