import pytest
from fastapi.testclient import TestClient
from shadow.api.server import app
from shadow.core.database import init_db
from shadow.core.telegram import telegram_companion
from shadow.memory.memory import memory_engine

client = TestClient(app)

@pytest.mark.asyncio
async def test_telegram_companion_command_handling():
    init_db()

    # 1. Test /help command
    reply = await telegram_companion.handle_text_message("/help", "12345")
    assert "🤖" in reply
    assert "`/today`" in reply

    # 2. Test /status command
    reply = await telegram_companion.handle_text_message("/status", "12345")
    assert "🔋" in reply
    assert "Active Goals" in reply

    # 3. Test /add command
    reply = await telegram_companion.handle_text_message("/add Read Python 3.12 release notes", "12345")
    assert "✅ Added task" in reply
    assert "Read Python 3.12 release notes" in reply

    # 4. Test /remind command
    reply = await telegram_companion.handle_text_message("/remind Call mom tonight", "12345")
    assert "🔔 Saved reminder" in reply
    assert "Call mom tonight" in reply

    # 5. Test /search command
    reply = await telegram_companion.handle_text_message("/search mom", "12345")
    assert "🔍" in reply
    assert "Call mom tonight" in reply

def test_mock_telegram_endpoint():
    init_db()

    # Test sending a mock Telegram message via the API endpoint
    response = client.post(
        "/telegram/mock_message",
        json={"text": "/help", "chat_id": "9999"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "🤖" in data["reply"]
