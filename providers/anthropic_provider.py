# -*- coding: utf-8 -*-
"""Anthropic provider implementation for models like KimiCode."""

from typing import Any
import openai
from .provider import Provider


class AnthropicProvider(Provider):
    """Anthropic protocol provider for models like KimiCode."""

    def __init__(self, **data: Any):
        """Initialize Anthropic provider."""
        data["provider_type"] = "anthropic"
        super().__init__(**data)

    async def check_connection(self) -> tuple[bool, str]:
        """Check if Anthropic connection works."""
        if not self.api_key:
            return False, "API Key is required"
        if not self.base_url:
            return False, "Base URL is required"
        if not self.model_id:
            return False, "Model ID is required"

        try:
            client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            # Try to list models or do a simple completion
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
            "model_type": "anthropic",
            "model_name": self.model_id,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "chat_model_class": "AnthropicChatModel",
        }
