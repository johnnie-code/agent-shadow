import os
import shutil
import pytest

# Ensure we use a test-specific shadow home directory before importing any shadow modules
TEST_SHADOW_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.test_shadow"))
os.environ["SHADOW_HOME"] = TEST_SHADOW_HOME

from shadow.core.config import get_config, reset_config

@pytest.fixture(autouse=True)
def setup_test_env():
    # Reset configuration to ensure the environment variable is picked up
    reset_config()
    config = get_config()

    # Ensure a clean slate
    if os.path.exists(TEST_SHADOW_HOME):
        try:
            shutil.rmtree(TEST_SHADOW_HOME)
        except Exception:
            pass
    os.makedirs(TEST_SHADOW_HOME, exist_ok=True)

    # Create subfolders like venv, config, memory, logs, cache, plugins, backups
    for folder in ["venv", "config", "memory", "logs", "cache", "plugins", "backups"]:
        os.makedirs(os.path.join(TEST_SHADOW_HOME, folder), exist_ok=True)

    yield

    # Clean up after the test
    if os.path.exists(TEST_SHADOW_HOME):
        try:
            shutil.rmtree(TEST_SHADOW_HOME)
        except Exception:
            pass
