import os
import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from shadow.providers.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_init():
    with patch.dict(
        os.environ,
        {
            "SHADOW_OLLAMA_MODE": "cloud",
            "SHADOW_OLLAMA_API_KEY": "test-key",
            "SHADOW_OLLAMA_BASE_URL": "https://custom-ollama.com",
            "SHADOW_OLLAMA_MODEL": "test-model-123",
        },
    ):
        provider = OllamaProvider()
        assert provider.mode == "cloud"
        assert provider.api_key == "test-key"
        assert provider.api_base == "https://custom-ollama.com"
        assert provider.model == "test-model-123"


@pytest.mark.asyncio
async def test_ollama_chat_success():
    with patch("httpx.AsyncClient.post") as mock_post:
        # Mock a successful non-streaming /api/chat response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "Hello from Ollama!"}
        }
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hi"}]
        res = await provider.chat(messages, endpoint="chat", stream=False)

        assert res["content"] == "Hello from Ollama!"
        assert "model" in res
        assert res["tokens_used"] > 0


@pytest.mark.asyncio
async def test_ollama_generate_success():
    with patch("httpx.AsyncClient.post") as mock_post:
        # Mock a successful /api/generate response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Generated text response"}
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hi"}]
        res = await provider.chat(messages, endpoint="generate", stream=False)

        assert res["content"] == "Generated text response"


@pytest.mark.asyncio
async def test_ollama_streaming_chat():
    with patch("httpx.AsyncClient.stream") as mock_stream:
        # Mock streaming response
        mock_response = MagicMock()
        mock_response.status_code = 200

        # We want aiter_lines() to return line-by-line JSON content
        async def mock_aiter_lines():
            lines = [
                json.dumps({"message": {"content": "Hello"}}),
                json.dumps({"message": {"content": " world"}}),
                json.dumps({"message": {"content": "!"}}),
            ]
            for line in lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        # We need AsyncClient.stream to be used as an async context manager
        class MockContextManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, exc_type, exc, tb):
                pass

        mock_stream.return_value = MockContextManager()

        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Stream me"}]

        chunks = []

        def callback(chunk):
            chunks.append(chunk)

        res = await provider.chat(
            messages, endpoint="chat", stream=True, stream_callback=callback
        )

        assert res["content"] == "Hello world!"
        assert chunks == ["Hello", " world", "!"]


@pytest.mark.asyncio
async def test_ollama_retries_and_success():
    with patch("httpx.AsyncClient.post") as mock_post:
        # First attempt raises timeout, second succeeds
        fail_response = httpx.ConnectTimeout("Timeout connecting")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "message": {"content": "Success after retry"}
        }

        mock_post.side_effect = [fail_response, success_response]

        provider = OllamaProvider()
        provider.max_retries = 2
        messages = [{"role": "user", "content": "hi"}]
        res = await provider._call_ollama_api(
            base_url="http://localhost:11434",
            model="llama3",
            messages=messages,
            endpoint="chat",
        )

        assert res["content"] == "Success after retry"
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_ollama_fallback_to_gemini():
    with patch("httpx.AsyncClient.post") as mock_post:
        # Mock Ollama post failing all retries
        mock_post.side_effect = httpx.ConnectError("Could not connect")

        provider = OllamaProvider()
        provider.max_retries = 1
        messages = [{"role": "user", "content": "hi"}]

        # Patch GeminiProvider's chat so we verify it falls back to Gemini
        with patch(
            "shadow.providers.google.GeminiProvider.chat", new_callable=AsyncMock
        ) as mock_gemini_chat:
            mock_gemini_chat.return_value = {
                "content": "Gemini fallback response",
                "tokens_used": 100,
                "estimated_cost": 0.001,
                "model": "gemini-2.5-flash",
            }

            res = await provider.chat(messages)
            assert res["content"] == "Gemini fallback response"
            mock_gemini_chat.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_fallback_all_the_way_to_mock():
    with patch("httpx.AsyncClient.post") as mock_post:
        # Mock Ollama post failing
        mock_post.side_effect = httpx.ConnectError("Could not connect")

        provider = OllamaProvider()
        provider.max_retries = 1
        messages = [{"role": "user", "content": "hi"}]

        # Force Gemini to fail too so it falls back to Mock
        with patch(
            "shadow.providers.google.GeminiProvider.chat",
            side_effect=Exception("Gemini Offline"),
        ):
            with patch(
                "shadow.providers.mock.MockProvider.chat", new_callable=AsyncMock
            ) as mock_mock_chat:
                mock_mock_chat.return_value = {
                    "content": "Mock fallback response",
                    "tokens_used": 150,
                    "estimated_cost": 0.0,
                    "model": "shadow-mock-model",
                }

                res = await provider.chat(messages)
                assert res["content"] == "Mock fallback response"
                mock_mock_chat.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_url_normalization():
    with patch.dict(
        os.environ, {"SHADOW_OLLAMA_MODE": "cloud", "SHADOW_OLLAMA_API_KEY": "test-key"}
    ):
        provider = OllamaProvider()

        # 1. No trailing slash, no /api
        url1 = provider._build_url("https://ollama.com", "chat")
        assert url1 == "https://ollama.com/api/chat"

        # 2. No trailing slash, with /api
        url2 = provider._build_url("https://ollama.com/api", "chat")
        assert url2 == "https://ollama.com/api/chat"

        # 3. With trailing slash, with /api/
        url3 = provider._build_url("https://ollama.com/api/", "chat")
        assert url3 == "https://ollama.com/api/chat"

        # 4. Generate endpoint
        url4 = provider._build_url("https://ollama.com/api/", "generate")
        assert url4 == "https://ollama.com/api/generate"


@pytest.mark.asyncio
async def test_ollama_cloud_unauthorized_propagation():
    with patch.dict(
        os.environ,
        {
            "SHADOW_OLLAMA_MODE": "cloud",
            "SHADOW_OLLAMA_API_KEY": "test-key",
            "SHADOW_OLLAMA_BASE_URL": "https://ollama.com",
        },
    ):
        provider = OllamaProvider()

        # Mock 401 Unauthorized
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Unauthorized API key"
            mock_resp.request = MagicMock(url="https://ollama.com/api/chat")

            # Raise HTTPStatusError when raise_for_status is called
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unauthorized", request=mock_resp.request, response=mock_resp
            )
            mock_post.return_value = mock_resp

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await provider.chat([{"role": "user", "content": "hi"}])

            assert exc_info.value.response.status_code == 401


@pytest.mark.asyncio
async def test_ollama_cloud_invalid_model_propagation():
    with patch.dict(
        os.environ, {"SHADOW_OLLAMA_MODE": "cloud", "SHADOW_OLLAMA_API_KEY": "test-key"}
    ):
        provider = OllamaProvider()

        # Mock 404 Not Found (Invalid Model)
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.text = "Model not found"
            mock_resp.request = MagicMock(url="https://ollama.com/api/chat")

            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Not Found", request=mock_resp.request, response=mock_resp
            )
            mock_post.return_value = mock_resp

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await provider.chat([{"role": "user", "content": "hi"}])

            assert exc_info.value.response.status_code == 404


@pytest.mark.asyncio
async def test_ollama_cloud_validation_missing_key():
    with patch.dict(os.environ, {"SHADOW_OLLAMA_MODE": "cloud"}, clear=True):
        # Temporarily clear env vars to force missing key
        if "SHADOW_OLLAMA_API_KEY" in os.environ:
            del os.environ["SHADOW_OLLAMA_API_KEY"]

        with pytest.raises(ValueError) as exc_info:
            OllamaProvider()
        assert "Missing SHADOW_OLLAMA_API_KEY" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_cloud_timeout_logging():
    with patch.dict(
        os.environ, {"SHADOW_OLLAMA_MODE": "cloud", "SHADOW_OLLAMA_API_KEY": "test-key"}
    ):
        provider = OllamaProvider()
        provider.max_retries = 1

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timed out")

            # Since timeout is transient, it should fall back to Gemini/Mock
            # Let's patch Gemini and Mock to check that we fall back
            with patch(
                "shadow.providers.google.GeminiProvider.chat", new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {"content": "Gemini Fallback"}
                res = await provider.chat([{"role": "user", "content": "hi"}])
                assert res["content"] == "Gemini Fallback"
                mock_gemini.assert_called_once()
