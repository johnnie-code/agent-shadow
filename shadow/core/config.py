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

BaseSettings = None
if IS_V2:
    try:
        from pydantic_settings import BaseSettings
    except ImportError:
        pass
else:
    try:
        from pydantic import BaseSettings
    except ImportError:
        pass

if BaseSettings is None:
    def _load_from_env(prefix: str, delimiter: str) -> dict:
        data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                stripped = key[len(prefix):]
                if not stripped:
                    continue
                parts = [p.lower() for p in stripped.split(delimiter)]
                current = data
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]

                val = value
                val_lower = val.lower()
                if val_lower == "true":
                    val = True
                elif val_lower == "false":
                    val = False
                elif val_lower == "none":
                    val = None
                else:
                    try:
                        if "." in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass
                current[parts[-1]] = val
        return data

    def _load_from_yaml() -> dict:
        data = {}
        yaml_paths = [
            os.path.join(SHADOW_HOME, "config", "config.yaml"),
            os.path.join(SHADOW_HOME, "config", "config.yml"),
            os.path.join(SHADOW_HOME, "config.yaml"),
            os.path.join(SHADOW_HOME, "config.yml"),
        ]
        custom_path = os.environ.get("SHADOW_CONFIG_YAML")
        if custom_path:
            yaml_paths.insert(0, custom_path)

        for path in yaml_paths:
            if os.path.exists(path):
                try:
                    import yaml
                    with open(path, "r", encoding="utf-8") as f:
                        loaded = yaml.safe_load(f)
                        if isinstance(loaded, dict):
                            def merge_dicts(dict1, dict2):
                                for k, v in dict2.items():
                                    if k in dict1 and isinstance(dict1[k], dict) and isinstance(v, dict):
                                        merge_dicts(dict1[k], v)
                                    else:
                                        dict1[k] = v
                            merge_dicts(data, loaded)
                except Exception:
                    pass
        return data

    class CompatibilityBaseSettings(BaseModel):
        def __init__(self, **kwargs):
            yaml_data = _load_from_yaml()

            config_cls = getattr(self, "Config", None)
            env_prefix = getattr(config_cls, "env_prefix", "SHADOW_")
            env_nested_delimiter = getattr(config_cls, "env_nested_delimiter", "__")
            env_data = _load_from_env(env_prefix, env_nested_delimiter)

            merged = {}
            def merge_dicts(target, source):
                for k, v in source.items():
                    if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                        merge_dicts(target[k], v)
                    else:
                        target[k] = v

            merge_dicts(merged, yaml_data)
            merge_dicts(merged, env_data)
            merge_dicts(merged, kwargs)

            super().__init__(**merged)

    BaseSettings = CompatibilityBaseSettings

if IS_V2:
    from pydantic import model_validator

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
