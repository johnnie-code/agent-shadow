import os
import pydantic
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

SHADOW_HOME = os.path.expanduser(os.environ.get("SHADOW_HOME", "~/.shadow"))

class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    model: str = "default-model"
    api_base: Optional[str] = None

# Check if Pydantic is v2
IS_V2 = pydantic.__version__.startswith("2.")

if IS_V2:
    from pydantic import model_validator
    from pydantic_settings import BaseSettings

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

        @model_validator(mode="after")
        def resolve_paths(self) -> 'ShadowConfig':
            if not os.path.isabs(self.db_path):
                self.db_path = os.path.abspath(os.path.join(SHADOW_HOME, self.db_path))
            if not os.path.isabs(self.data_dir):
                self.data_dir = os.path.abspath(os.path.join(SHADOW_HOME, self.data_dir))
            return self

        class Config:
            env_prefix = "SHADOW_"
            env_nested_delimiter = "__"
else:
    from pydantic import root_validator
    from pydantic import BaseSettings

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

        @root_validator(pre=False)
        def resolve_paths(cls, values):
            db_path = values.get("db_path", "shadow.db")
            data_dir = values.get("data_dir", ".")
            if not os.path.isabs(db_path):
                values["db_path"] = os.path.abspath(os.path.join(SHADOW_HOME, db_path))
            if not os.path.isabs(data_dir):
                values["data_dir"] = os.path.abspath(os.path.join(SHADOW_HOME, data_dir))
            return values

        class Config:
            env_prefix = "SHADOW_"
            env_nested_delimiter = "__"

# Singleton configuration
_config: Optional[ShadowConfig] = None

def get_config() -> ShadowConfig:
    global _config
    if _config is None:
        try:
            from dotenv import load_dotenv
            shadow_home_env = os.path.join(SHADOW_HOME, "config", ".env")
            if os.path.exists(shadow_home_env):
                load_dotenv(shadow_home_env)
            else:
                data_dir = os.environ.get("SHADOW_DATA_DIR", ".")
                env_path = os.path.join(data_dir, ".env")
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                else:
                    load_dotenv()
        except ImportError:
            pass
        _config = ShadowConfig()
    return _config

def reset_config(new_config: Optional[ShadowConfig] = None):
    global _config
    _config = new_config
