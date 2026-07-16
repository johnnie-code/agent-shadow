import pytest
from shadow.providers.factory import get_provider
from shadow.providers.mock import MockProvider

@pytest.mark.asyncio
async def test_mock_provider():
    provider = get_provider("mock")
    assert isinstance(provider, MockProvider)

    response = await provider.chat([{"role": "user", "content": "Hello"}])
    assert "Mock response" in response["content"]
    assert response["tokens_used"] == 150
    assert response["estimated_cost"] == 0.0

@pytest.mark.asyncio
async def test_mock_json_response():
    provider = get_provider("mock")
    response = await provider.chat([{"role": "user", "content": "Return a JSON formatted list of goals"}])
    assert "success" in response["content"]
    assert "MEXT" in response["content"]
