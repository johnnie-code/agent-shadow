import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    model: str = "default-model"
    api_base: Optional[str] = None

class ShadowConfig(BaseSettings):
    # App Settings
    app_name: str = "Shadow"
    db_path: str = "shadow.db"
    log_level: str = "INFO"
    data_dir: str = "."

    # Provider Configurations
    openai: ProviderConfig = Field(default_factory=lambda: ProviderConfig(model="gpt-4o-mini"))
    anthropic: ProviderConfig = Field(default_factory=lambda: ProviderConfig(model="claude-3-5-sonnet-latest"))
    gemini: ProviderConfig = Field(default_factory=lambda: ProviderConfig(model="gemini-2.5-flash"))
    default_provider: str = "mock"  # Can be mock, openai, anthropic, gemini

    # System Preferences & Limits
    battery_limit: int = 20  # Stop high battery drain tools under 20%
    internet_usage: bool = True
    notification_preferences: str = "terminal"  # terminal, android, none

    # Schedules
    scan_interval_seconds: int = 3600  # 1 hour
    reflection_time: str = "22:00"  # HH:MM daily format

    class Config:
        env_prefix = "SHADOW_"
        env_nested_delimiter = "__"

# Singleton configuration
_config: Optional[ShadowConfig] = None

def get_config() -> ShadowConfig:
    global _config
    if _config is None:
        # Load from environment variables by default, can be extended to yaml/json
        _config = ShadowConfig()
    return _config

def reset_config(new_config: Optional[ShadowConfig] = None):
    global _config
    _config = new_config
