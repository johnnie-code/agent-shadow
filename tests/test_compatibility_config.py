import os
import sys
from unittest.mock import patch, MagicMock
import pytest

def test_compatibility_base_settings_fallback(monkeypatch):
    # Ensure any cached module is removed so we get fresh imports
    if 'shadow.core.config' in sys.modules:
        del sys.modules['shadow.core.config']

    # Mock pydantic_settings to raise ImportError on import
    with patch.dict(sys.modules, {'pydantic_settings': None}):
        from shadow.core.config import get_config, reset_config

        # Reset and clear config
        reset_config(None)

        # Set some environment variables to verify that the fallback loader picks them up
        monkeypatch.setenv("SHADOW_APP_NAME", "Fallback Shadow OS")
        monkeypatch.setenv("SHADOW_OPENAI__MODEL", "gpt-fallback-model")
        monkeypatch.setenv("SHADOW_BATTERY_LIMIT", "15")

        # Try loading configuration
        config = get_config()

        # Assertions
        assert config.app_name == "Fallback Shadow OS"
        assert config.openai.model == "gpt-fallback-model"
        assert config.battery_limit == 15

        # Reset config afterwards
        reset_config(None)
