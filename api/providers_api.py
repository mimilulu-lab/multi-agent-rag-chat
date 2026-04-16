# -*- coding: utf-8 -*-
"""API routes for providers configuration."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from providers import ProviderManager, ProviderType

router = APIRouter(prefix="/api/providers", tags=["providers"])


def get_provider_manager() -> ProviderManager:
    """Get the provider manager instance."""
    return ProviderManager()


class CreateProviderRequest(BaseModel):
    """Request to create a provider."""
    provider_type: ProviderType = Field(..., description="Provider type: dashscope or anthropic")
    name: str = Field(default="", description="Display name for this provider")
    api_key: str = Field(..., description="API key")
    base_url: str = Field(default="", description="Base URL (required for anthropic)")
    model_id: str = Field(..., description="Model ID for API calls")
    model_name: str = Field(default="", description="Model display name")


class UpdateProviderRequest(BaseModel):
    """Request to update a provider."""
    name: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    model_id: Optional[str] = Field(default=None)
    model_name: Optional[str] = Field(default=None)


class SetActiveRequest(BaseModel):
    """Request to set active provider."""
    provider_id: str = Field(..., description="Provider ID to activate")


class TestConnectionResponse(BaseModel):
    """Connection test response."""
    success: bool
    message: str


@router.get("")
async def list_providers():
    """List all configured providers."""
    manager = get_provider_manager()
    providers = manager.list_providers()
    active = manager.get_active_provider()
    return {
        "providers": providers,
        "active_provider_id": active.id if active else None,
    }


@router.post("")
async def create_provider(request: CreateProviderRequest):
    """Create a new provider."""
    manager = get_provider_manager()
    try:
        provider = manager.add_provider(request.model_dump())
        return provider.to_info(mask_secret=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{provider_id}")
async def update_provider(provider_id: str, request: UpdateProviderRequest):
    """Update a provider."""
    manager = get_provider_manager()
    # Get non-null values
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    provider = manager.update_provider(provider_id, update_data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider.to_info(mask_secret=True)


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str):
    """Delete a provider."""
    manager = get_provider_manager()
    success = manager.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"success": True}


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str):
    """Test a provider connection."""
    manager = get_provider_manager()
    import asyncio
    success, message = await manager.test_provider(provider_id)
    return TestConnectionResponse(success=success, message=message)


@router.post("/active")
async def set_active_provider(request: SetActiveRequest):
    """Set the active provider."""
    manager = get_provider_manager()
    success = manager.set_active_provider(request.provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider = manager.get_active_provider()
    return {
        "success": True,
        "active_provider": provider.to_info(mask_secret=True) if provider else None,
    }


@router.get("/active")
async def get_active_provider():
    """Get the currently active provider."""
    manager = get_provider_manager()
    provider = manager.get_active_provider()
    if not provider:
        return {"active_provider": None}
    return {
        "active_provider": provider.to_info(mask_secret=True),
    }


class TestConnectionRequest(BaseModel):
    """Request to test provider connection without saving."""
    provider_type: ProviderType = Field(..., description="Provider type: dashscope or anthropic")
    api_key: str = Field(..., description="API key")
    base_url: str = Field(default="", description="Base URL (required for anthropic)")
    model_id: str = Field(..., description="Model ID for API calls")


@router.post("/test-connection")
async def test_connection_temp(request: TestConnectionRequest):
    """Test connection without saving (temporary provider)."""
    from providers import DashScopeProvider, AnthropicProvider

    try:
        if request.provider_type == ProviderType.DASHSCOPE:
            provider = DashScopeProvider(
                id="test",
                name="Test Provider",
                api_key=request.api_key,
                model_id=request.model_id,
                model_name="Test Model",
            )
        elif request.provider_type == ProviderType.ANTHROPIC:
            provider = AnthropicProvider(
                id="test",
                name="Test Provider",
                api_key=request.api_key,
                base_url=request.base_url,
                model_id=request.model_id,
                model_name="Test Model",
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider type: {request.provider_type}")

        success, message = await provider.check_connection()
        return TestConnectionResponse(success=success, message=message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/types")
async def get_provider_types():
    """Get available provider types."""
    return {
        "types": [
            {
                "id": "dashscope",
                "name": "阿里云 DashScope",
                "description": "阿里云大模型服务平台",
                "required_fields": ["name", "api_key", "model_id", "model_name"],
                "optional_fields": [],
            },
            {
                "id": "anthropic",
                "name": "Anthropic 协议",
                "description": "支持 Anthropic Claude API 协议的模型，如 KimiCode",
                "required_fields": ["name", "api_key", "base_url", "model_id", "model_name"],
                "optional_fields": [],
            },
        ]
    }


# ========== Embedding Provider Endpoints ==========

@router.get("/embedding")
async def get_embedding_provider():
    """Get the currently active embedding provider."""
    manager = get_provider_manager()
    provider = manager.get_embedding_provider()
    return {
        "embedding_provider": provider.to_info(mask_secret=True) if provider else None,
    }


@router.post("/embedding")
async def set_embedding_provider(request: SetActiveRequest):
    """Set the active embedding provider."""
    manager = get_provider_manager()
    success = manager.set_embedding_provider(request.provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider = manager.get_embedding_provider()
    return {
        "success": True,
        "embedding_provider": provider.to_info(mask_secret=True) if provider else None,
    }


@router.get("/embedding/types")
async def get_embedding_provider_types():
    """Get available provider types for embedding (currently only DashScope)."""
    return {
        "types": [
            {
                "id": "dashscope",
                "name": "阿里云 DashScope",
                "description": "阿里云 DashScope 文本嵌入模型",
                "required_fields": ["name", "api_key", "model_id", "model_name"],
                "optional_fields": [],
                "supported_models": [
                    {"id": "text-embedding-v4", "name": "Text Embedding V4 (推荐)"},
                    {"id": "text-embedding-v3", "name": "Text Embedding V3"},
                    {"id": "text-embedding-v2", "name": "Text Embedding V2"},
                ],
            },
        ]
    }
