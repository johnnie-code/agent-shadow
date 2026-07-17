import os
import json
import time
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from shadow.providers.base import BaseProvider
from shadow.core.config import get_config
from shadow.core.logging import log_decision, logger

class OllamaProvider(BaseProvider):
    def __init__(self):
        config = get_config()
        # Retrieve configuration from config/env
        # Check if Ollama config exists in config; if not, fall back to defaults
        ollama_config = getattr(config, "ollama", None)

        self.mode = os.environ.get("SHADOW_OLLAMA_MODE") or (ollama_config.mode if ollama_config else "local")
        self.mode = self.mode.lower()

        self.api_key = os.environ.get("SHADOW_OLLAMA_API_KEY") or (ollama_config.api_key if ollama_config else None)

        env_base_url = os.environ.get("SHADOW_OLLAMA_BASE_URL")
        if env_base_url:
            self.api_base = env_base_url
        elif ollama_config and ollama_config.api_base:
            self.api_base = ollama_config.api_base
        else:
            self.api_base = "https://ollama.com/api" if self.mode == "cloud" else "http://localhost:11434"

        self.model = os.environ.get("SHADOW_OLLAMA_MODEL") or (ollama_config.model if ollama_config else None)
        if not self.model:
            self.model = "gpt-oss:120b-cloud" if self.mode == "cloud" else "llama3"

        # Defaults for robustness
        self.timeout = 30.0
        self.max_retries = 3

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # Ollama is typically free/local, so cost is 0.0.
        # For Ollama Cloud, let's assume a mock small pricing or 0.0.
        return 0.0

    async def _call_ollama_api(
        self,
        base_url: str,
        model: str,
        messages: List[Dict[str, str]],
        endpoint: str = "chat",
        stream: bool = False,
        stream_callback = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Low-level helper to invoke Ollama API (either chat or generate) with retries and timeout.
        """
        url = f"{base_url.rstrip('/')}/api/{endpoint}"

        # Prepare payload
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", model),
            "stream": stream,
        }

        if endpoint == "chat":
            payload["messages"] = messages
        else:
            # For generate, construct a prompt from messages
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user").upper()
                content = msg.get("content", "")
                prompt_parts.append(f"{role}: {content}")
            payload["prompt"] = "\n".join(prompt_parts)

        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error = None
        backoff = 1.0

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    if stream:
                        # Handle streaming response
                        full_content = ""
                        async with client.stream(
                            "POST", url, json=payload, headers=headers, timeout=self.timeout
                        ) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if not line:
                                    continue
                                try:
                                    data = json.loads(line)
                                    chunk = ""
                                    if endpoint == "chat":
                                        chunk = data.get("message", {}).get("content", "")
                                    else:
                                        chunk = data.get("response", "")

                                    full_content += chunk
                                    if stream_callback:
                                        stream_callback(chunk)
                                except Exception as json_err:
                                    logger.warning(f"Failed to parse streaming line: {line}. Error: {json_err}")

                            return {
                                "content": full_content,
                                "tokens_used": len(full_content.split()) * 2,  # Rough estimation of tokens
                                "estimated_cost": 0.0,
                                "model": payload["model"]
                            }
                    else:
                        # Standard unary request
                        response = await client.post(
                            url, json=payload, headers=headers, timeout=self.timeout
                        )
                        response.raise_for_status()
                        data = response.json()

                        if endpoint == "chat":
                            content = data.get("message", {}).get("content", "")
                        else:
                            content = data.get("response", "")

                        # Calculate rough token usage
                        prompt_len = sum(len(m.get("content", "").split()) for m in messages)
                        completion_len = len(content.split())
                        tokens_used = int((prompt_len + completion_len) * 1.3)

                        return {
                            "content": content,
                            "tokens_used": tokens_used,
                            "estimated_cost": 0.0,
                            "model": payload["model"]
                        }

            except (httpx.HTTPError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    break

        raise last_error or RuntimeError("Failed to connect to Ollama after multiple retries.")

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Sends a chat message to the Ollama provider.
        Supports fallback sequence: Ollama Cloud -> Ollama Local -> Gemini -> Mock
        """
        call_kwargs = kwargs.copy()
        endpoint = call_kwargs.pop("endpoint", "chat")
        stream = call_kwargs.pop("stream", False)
        stream_callback = call_kwargs.pop("stream_callback", None)

        # 1. Determine fallback chain based on configuration mode
        fallback_chain = []
        if self.mode == "cloud":
            fallback_chain.append({
                "name": "Ollama Cloud",
                "api_base": self.api_base,
                "model": self.model
            })
            # Add Ollama Local as a secondary fallback
            config = get_config()
            ollama_config = getattr(config, "ollama", None)
            local_base = (ollama_config.api_base if ollama_config and ollama_config.mode == "local" else None) or "http://localhost:11434"
            local_model = (ollama_config.model if ollama_config and ollama_config.mode == "local" else None) or "llama3"
            fallback_chain.append({
                "name": "Ollama Local",
                "api_base": local_base,
                "model": local_model
            })
        else:
            fallback_chain.append({
                "name": "Ollama Local",
                "api_base": self.api_base,
                "model": self.model
            })

        # 2. Try Ollama providers in sequence
        last_exception = None
        for provider_info in fallback_chain:
            try:
                log_decision(
                    "INFO",
                    f"Attempting chat with {provider_info['name']}",
                    reasoning=f"Using model {provider_info['model']} at {provider_info['api_base']}"
                )
                res = await self._call_ollama_api(
                    base_url=provider_info["api_base"],
                    model=provider_info["model"],
                    messages=messages,
                    endpoint=endpoint,
                    stream=stream,
                    stream_callback=stream_callback,
                    **call_kwargs
                )
                return res
            except Exception as e:
                last_exception = e
                log_decision(
                    "WARNING",
                    f"{provider_info['name']} failed",
                    reasoning=f"Error encountered: {e}. Falling back to next provider in sequence."
                )

        # 3. Fallback to Gemini
        try:
            log_decision("INFO", "Falling back to Gemini", reasoning="Both Ollama Cloud and Ollama Local are unavailable.")
            from shadow.providers.google import GeminiProvider
            gemini = GeminiProvider()
            return await gemini.chat(messages, **kwargs)
        except Exception as e:
            log_decision("WARNING", "Gemini fallback failed", reasoning=f"Error: {e}. Falling back to Mock.")

        # 4. Fallback to Mock
        from shadow.providers.mock import MockProvider
        mock_prov = MockProvider()
        return await mock_prov.chat(messages, **kwargs)
