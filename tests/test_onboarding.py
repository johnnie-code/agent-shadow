import os
import pytest
from shadow.core.config import SHADOW_HOME, reset_config, get_config
from shadow.core.database import init_db, get_db_connection
from shadow.cli.onboard import run_onboarding
from shadow.memory.memory import memory_engine

def test_onboarding_non_interactive():
    # Setup clean sandbox DB and configurations
    reset_config(None)
    init_db()

    # Define mock defaults
    defaults = {
        "user_name": "Test Pilot",
        "assistant_name": "Jules-AI",
        "life_mission": "Test the entire shadow OS codebase perfectly",
        "goals": ["Achieve 100% test coverage", "Ensure robust error handling"],
        "projects": ["Onboarding suite", "Telegram companion suite"],
        "provider": "mock",
        "api_key": "",
        "telegram_enabled": False,
        "notification_pref": "terminal"
    }

    # Run onboarding in non-interactive mode
    run_onboarding(interactive=False, defaults=defaults)

    # 1. Verify files are created
    env_path = os.path.join(SHADOW_HOME, "config", ".env")
    mission_path = os.path.join(SHADOW_HOME, "mission.md")
    assert os.path.exists(env_path)
    assert os.path.exists(mission_path)

    # 2. Verify config is reloaded and matches
    reset_config(None)
    config = get_config()
    assert config.user_name == "Test Pilot"
    assert config.assistant_name == "Jules-AI"
    assert config.life_mission == "Test the entire shadow OS codebase perfectly"

    # 3. Verify memory key is recorded
    mem = memory_engine.get_memory_by_key("onboarding_completed")
    assert mem is not None
    assert mem["content"] == "true"

    # 4. Verify goals are synchronized to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM goals")
    goals = cursor.fetchall()
    conn.close()

    assert len(goals) > 0
    goal_titles = [g["title"] for g in goals]
    assert "Achieve 100% test coverage" in goal_titles
    assert "Ensure robust error handling" in goal_titles
