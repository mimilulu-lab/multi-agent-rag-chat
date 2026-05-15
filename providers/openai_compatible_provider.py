# -*- coding: utf-8 -*-
"""OpenAI and custom OpenAI-compatible provider implementation."""

from typing import Any, ClassVar
import openai
from .provider import Provider


class OpenAICompatibleProvider(Provider):
    """Provider for OpenAI and any OpenAI-compatible API."""

    OPENAI_BASE_URL: ClassVar[str] = "https://api.openai.com/v1"

    def __init__(self, **data: Any):
        """Initialize OpenAI-compatible provider."""
        # provider_type must be set by caller (openai or custom)
        if not data.get("provider_type"):
            data["provider_type"] = "openai"
        if not data.get("base_url"):
            data["base_url"] = self.OPENAI_BASE_URL
        super().__init__(**data)

    async def check_connection(self) -> tuple[bool, str]:
        """Check if the connection works."""
        if not self.api_key:
            return False, "API Key is required"
        if not self.model_id:
            return False, "Model ID is required"
        if not self.base_url:
            return False, "Base URL is required"

        try:
            client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            await client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_chat_model_config(self) -> dict:
        """Get chat model configuration for agentscope."""
        return {
            "model_type": "openai",
            "model_name": self.model_id,
            "api_key": self.api_key,
            "base_url": self.base_url,
        }
