# -*- coding: utf-8 -*-
"""Kimi (Moonshot) provider implementation."""

from typing import Any, ClassVar
import openai
from .provider import Provider


class KimiProvider(Provider):
    """Kimi provider for Moonshot AI models."""

    KIMI_BASE_URL: ClassVar[str] = "https://api.moonshot.cn/v1"

    def __init__(self, **data: Any):
        """Initialize Kimi provider."""
        data["provider_type"] = "kimi"
        if not data.get("base_url"):
            data["base_url"] = self.KIMI_BASE_URL
        super().__init__(**data)

    async def check_connection(self) -> tuple[bool, str]:
        """Check if Kimi connection works."""
        if not self.api_key:
            return False, "API Key is required"
        if not self.model_id:
            return False, "Model ID is required"

        try:
            client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.KIMI_BASE_URL
            )
            # Try a simple chat completion
            response = await client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5
            )
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_chat_model_config(self) -> dict:
        """Get chat model configuration for agentscope."""
        return {
            "model_type": "openai",  # Kimi uses OpenAI-compatible API
            "model_name": self.model_id,
            "api_key": self.api_key,
            "base_url": self.KIMI_BASE_URL,
        }
