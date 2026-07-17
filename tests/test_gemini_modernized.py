import os
import json
import time
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from shadow.providers.google import GeminiProvider, STATIC_FALLBACK_MODELS
from shadow.providers.mock import MockProvider
from shadow.providers.openai import OpenAIProvider
from shadow.core.config import get_config

@pytest.fixture(autouse=True)
def setup_env():
    os.environ["SHADOW_GEMINI_API_KEY"] = "dummy-api-key"
    os.environ["SHADOW_GEMINI_AUTO_DISCOVER"] = "false"
    yield
    if "SHADOW_GEMINI_API_KEY" in os.environ:
        del os.environ["SHADOW_GEMINI_API_KEY"]
    if "SHADOW_GEMINI_AUTO_DISCOVER" in os.environ:
        del os.environ["SHADOW_GEMINI_AUTO_DISCOVER"]

@pytest.mark.asyncio
async def test_successful_generate_content():
    provider = GeminiProvider()
    provider.auto_discover = False

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Hello from Gemini!"}
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 5,
            "totalTokenCount": 15
        }
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await provider.chat([{"role": "user", "content": "hello"}], model="gemini-2.5-flash")

        assert result["content"] == "Hello from Gemini!"
        assert result["tokens_used"] == 15
        assert result["model"] == "gemini-2.5-flash"

        args, kwargs = mock_post.call_args
        assert "models/gemini-2.5-flash:generateContent" in args[0]
        assert "key=dummy-api-key" in args[0]

@pytest.mark.asyncio
async def test_invalid_api_key_switching_provider():
    provider = GeminiProvider()
    provider.auto_discover = False

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "API key not valid"

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with patch.object(provider, "_get_fallback_provider", return_value=MockProvider()):
            result = await provider.chat([{"role": "user", "content": "hello"}])
            assert "Mock response" in result["content"]

@pytest.mark.asyncio
async def test_404_model_not_found_fallback():
    provider = GeminiProvider()
    provider.auto_discover = False

    res_404 = MagicMock()
    res_404.status_code = 404
    res_404.text = "Model not found"

    res_200 = MagicMock()
    res_200.status_code = 200
    res_200.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Fallback success!"}
                    ]
                }
            }
        ]
    }

    call_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return res_404
        return res_200

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        result = await provider.chat([{"role": "user", "content": "hello"}], model="gemini-non-existent")

        assert result["content"] == "Fallback success!"
        assert result["model"] == "gemini-flash-latest"
        assert call_count == 2

@pytest.mark.asyncio
async def test_429_rate_limit_retry():
    provider = GeminiProvider()
    provider.auto_discover = False
    provider.max_retries = 2

    res_429 = MagicMock()
    res_429.status_code = 429
    res_429.text = "Quota exceeded"

    res_200 = MagicMock()
    res_200.status_code = 200
    res_200.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Success after rate limit!"}
                    ]
                }
            }
        ]
    }

    call_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return res_429
        return res_200

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with patch("asyncio.sleep", AsyncMock()):
            result = await provider.chat([{"role": "user", "content": "hello"}], model="gemini-2.5-flash")
            assert result["content"] == "Success after rate limit!"
            assert call_count == 2

@pytest.mark.asyncio
async def test_500_server_error_retry():
    provider = GeminiProvider()
    provider.auto_discover = False
    provider.max_retries = 2

    res_500 = MagicMock()
    res_500.status_code = 500
    res_500.text = "Internal error"

    res_200 = MagicMock()
    res_200.status_code = 200
    res_200.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Success after server error!"}
                    ]
                }
            }
        ]
    }

    call_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return res_500
        return res_200

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with patch("asyncio.sleep", AsyncMock()):
            result = await provider.chat([{"role": "user", "content": "hello"}], model="gemini-2.5-flash")
            assert result["content"] == "Success after server error!"
            assert call_count == 2

@pytest.mark.asyncio
async def test_dynamic_model_discovery():
    provider = GeminiProvider()
    provider.auto_discover = True

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {
        "models": [
            {
                "name": "models/gemini-new-experimental",
                "description": "Next generation coding model with thinking.",
                "supportedGenerationMethods": ["generateContent"]
            }
        ]
    }

    save_cache_mock = MagicMock()
    provider._save_cache = save_cache_mock

    with patch("httpx.AsyncClient.get", return_value=mock_models_response):
        discovered = await provider.discover_models()

        assert "gemini-new-experimental" in discovered
        capabilities = discovered["gemini-new-experimental"]["capabilities"]
        assert capabilities["supports_thinking"] is True
        assert capabilities["supports_code_execution"] is False

        save_cache_mock.assert_called_once()
