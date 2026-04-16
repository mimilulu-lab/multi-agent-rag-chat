# -*- coding: utf-8 -*-
"""API routes for Manager Agent configuration."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config.manager_config import manager_config_manager, ManagerConfig

router = APIRouter(prefix="/api/manager", tags=["manager"])


class UpdateManagerRequest(BaseModel):
    """更新 Manager 配置请求"""
    name: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    personality: Optional[str] = Field(default=None)
    avatar_type: Optional[str] = Field(default=None)
    provider_id: Optional[str] = Field(default=None)
    kb_id: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class TestConnectionResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str


@router.get("")
async def get_manager_config():
    """获取 Manager 配置"""
    return manager_config_manager.to_info()


@router.put("")
async def update_manager_config(request: UpdateManagerRequest):
    """更新 Manager 配置"""
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    config = manager_config_manager.update_config(update_data)

    return {
        "id": "manager_default",
        "name": config.name,
        "role": config.role,
        "personality": config.personality,
        "avatar_type": config.avatar_type,
        "agent_type": "manager",
        "provider_id": config.provider_id,
        "is_active": config.is_active,
    }


@router.post("/test")
async def test_manager_connection():
    """测试 Manager 的模型连接"""
    config = manager_config_manager.get_config()

    if not config.provider_id:
        return TestConnectionResponse(success=False, message="未配置 Provider")

    # 通过 provider_id 获取 Provider 信息
    from providers import provider_manager
    provider = provider_manager.get_provider(config.provider_id)

    if not provider:
        return TestConnectionResponse(success=False, message=f"Provider {config.provider_id} 不存在")

    # 导入测试连接函数
    from providers import test_model_connection

    success, message = await test_model_connection(
        provider_type=provider.provider_type,
        api_key=provider.api_key,
        model_id=provider.model_id,
        base_url=provider.base_url if provider.base_url else None
    )

    return TestConnectionResponse(success=success, message=message)
