import pytest
from fastapi.testclient import TestClient
from shadow.api.server import app
from shadow.core.database import init_db

client = TestClient(app)

def test_api_status_and_goals():
    init_db()

    # 1. Test status
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "pending_tasks" in data

    # 2. Test goals listing endpoint
    response_goals = client.get("/goals")
    assert response_goals.status_code == 200
    assert response_goals.json()["success"] is True
