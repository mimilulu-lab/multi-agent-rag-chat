# -*- coding: utf-8 -*-
"""Base provider definition."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, ClassVar
from pydantic import BaseModel, Field, ConfigDict


class ModelInfo(BaseModel):
    """Model information."""
    id: str = Field(..., description="Model identifier used in API calls")
    name: str = Field(..., description="Human-readable model name")


class ProviderInfo(BaseModel):
    """Provider information for serialization."""
    id: str = Field(..., description="Provider identifier")
    name: str = Field(default="", description="Human-readable provider name")
    provider_type: str = Field(..., description="Provider type: dashscope or anthropic")
    base_url: str = Field(default="", description="API base URL")
    api_key: str = Field(default="", description="API key for authentication")
    model_id: str = Field(..., description="Model ID")
    model_name: str = Field(default="", description="Model display name")
    is_active: bool = Field(default=False, description="Whether this provider is currently active")


class Provider(BaseModel, ABC):
    """Base class for model providers."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(default="", description="Display name")
    provider_type: str = Field(..., description="Provider type")
    base_url: str = Field(default="")
    api_key: str = Field(default="")
    model_id: str = Field(..., description="Model ID for API calls")
    model_name: str = Field(default="", description="Model display name")
    is_active: bool = Field(default=False)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    async def check_connection(self) -> tuple[bool, str]:
        """Check if the provider connection works."""
        pass

    def to_info(self, mask_secret: bool = True) -> ProviderInfo:
        """Convert to ProviderInfo."""
        return ProviderInfo(
            id=self.id,
            name=self.name or self.model_id,
            provider_type=self.provider_type,
            base_url=self.base_url,
            api_key="***" if mask_secret and self.api_key else self.api_key,
            model_id=self.model_id,
            model_name=self.model_name or self.model_id,
            is_active=self.is_active,
        )

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update configuration."""
        if "name" in config and config["name"] is not None:
            self.name = str(config["name"])
        if "model_id" in config and config["model_id"] is not None:
            self.model_id = str(config["model_id"])
        if "model_name" in config and config["model_name"] is not None:
            self.model_name = str(config["model_name"])
        if "api_key" in config and config["api_key"] is not None:
            self.api_key = str(config["api_key"])
        if "base_url" in config and config["base_url"] is not None:
            self.base_url = str(config["base_url"])
