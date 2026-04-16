# -*- coding: utf-8 -*-
"""DashScope provider implementation."""

from typing import Any, ClassVar
import openai
from .provider import Provider


class DashScopeProvider(Provider):
    """DashScope provider for Alibaba Cloud models."""

    DASHSCOPE_BASE_URL: ClassVar[str] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, **data: Any):
        """Initialize DashScope provider."""
        data["provider_type"] = "dashscope"
        super().__init__(**data)

    async def check_connection(self) -> tuple[bool, str]:
        """Check if DashScope connection works."""
        if not self.api_key:
            return False, "API Key is required"
        if not self.model_id:
            return False, "Model ID is required"

        try:
            client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.DASHSCOPE_BASE_URL
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
            "model_type": "dashscope",
            "model_name": self.model_id,
            "api_key": self.api_key,
        }
