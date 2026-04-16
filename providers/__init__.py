# -*- coding: utf-8 -*-
"""Providers module for model configuration."""

import openai
from typing import Optional

from .provider import Provider, ModelInfo, ProviderInfo
from .dashscope_provider import DashScopeProvider
from .anthropic_provider import AnthropicProvider
from .kimi_provider import KimiProvider
from .provider_manager import ProviderManager, ProviderType, provider_manager


async def test_model_connection(
    provider_type: str,
    api_key: str,
    model_id: str,
    base_url: Optional[str] = None
) -> tuple[bool, str]:
    """Test model connection without creating a provider.

    Args:
        provider_type: Provider type (dashscope, anthropic, openai, custom)
        api_key: API key
        model_id: Model ID
        base_url: Optional base URL

    Returns:
        Tuple of (success, message)
    """
    if not api_key:
        return False, "API Key is required"
    if not model_id:
        return False, "Model ID is required"

    # Determine base URL based on provider type
    if provider_type == "dashscope":
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    elif provider_type == "kimi":
        base_url = "https://api.moonshot.cn/v1"
    elif provider_type in ["anthropic", "custom"] and not base_url:
        return False, "Base URL is required for this provider type"

    try:
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        # Try a simple chat completion
        response = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5
        )
        return True, "Connection successful"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


__all__ = [
    "Provider",
    "ModelInfo",
    "ProviderInfo",
    "DashScopeProvider",
    "AnthropicProvider",
    "KimiProvider",
    "ProviderManager",
    "ProviderType",
    "provider_manager",
    "test_model_connection",
]