import pytest
from shadow.providers.manager import ProviderManager, provider_manager
from shadow.providers.mock import MockProvider

@pytest.mark.asyncio
async def test_provider_manager_routing():
    pm = ProviderManager()

    # Test routing offline tasks to Ollama
    offline_provider = pm.route_provider("offline")
    assert offline_provider.__class__.__name__ == "OllamaProvider"

    # Test routing conversation
    pm.set_default_provider("mock")
    conv_prov = pm.route_provider("conversation")
    assert conv_prov.__class__.__name__ == "MockProvider"

@pytest.mark.asyncio
async def test_provider_manager_fallback():
    pm = ProviderManager()

    # Register standard fallback check
    messages = [{"role": "user", "content": "Hello fallback"}]
    res = await pm.chat(messages, provider_override="mock")
    assert "Mock response" in res["content"] or "Mock structured" in res["content"]

def test_provider_manager_metrics():
    pm = ProviderManager()
    pm._record_metric("MockProvider", 0.05, 100, 0.001, True)

    summary = pm.get_metrics_summary()
    assert summary["total_requests"] == 1
    assert summary["success_rate"] == 1.0
    assert summary["total_cost"] == 0.001
