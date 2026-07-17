import os
import json
import time
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from shadow.providers.base import BaseProvider
from shadow.core.config import get_config, SHADOW_HOME
from shadow.core.logging import log_decision, logger

STATIC_FALLBACK_MODELS = {
    "gemini-2.5-flash": {
        "name": "models/gemini-2.5-flash",
        "short_name": "gemini-2.5-flash",
        "capabilities": {
            "supports_thinking": False,
            "supports_image": True,
            "supports_tools": True,
            "supports_function_calling": True,
            "supports_code_execution": True,
            "supports_computer_use": False
        }
    },
    "gemini-flash-latest": {
        "name": "models/gemini-flash-latest",
        "short_name": "gemini-flash-latest",
        "capabilities": {
            "supports_thinking": False,
            "supports_image": True,
            "supports_tools": True,
            "supports_function_calling": True,
            "supports_code_execution": True,
            "supports_computer_use": False
        }
    },
    "gemini-2.5-flash-lite": {
        "name": "models/gemini-2.5-flash-lite",
        "short_name": "gemini-2.5-flash-lite",
        "capabilities": {
            "supports_thinking": False,
            "supports_image": True,
            "supports_tools": True,
            "supports_function_calling": True,
            "supports_code_execution": True,
            "supports_computer_use": False
        }
    },
    "gemini-2.0-flash": {
        "name": "models/gemini-2.0-flash",
        "short_name": "gemini-2.0-flash",
        "capabilities": {
            "supports_thinking": False,
            "supports_image": True,
            "supports_tools": True,
            "supports_function_calling": True,
            "supports_code_execution": True,
            "supports_computer_use": False
        }
    }
}

class GeminiProvider(BaseProvider):
    def __init__(self):
        config = get_config()
        self.api_key = os.environ.get("SHADOW_GEMINI_API_KEY") or (config.gemini.api_key if config.gemini else None)
        self.model = os.environ.get("SHADOW_GEMINI_MODEL") or (config.gemini.model if config.gemini else "gemini-2.5-flash")
        self.api_base = os.environ.get("SHADOW_GEMINI_API_BASE") or (config.gemini.api_base if config.gemini else None) or "https://generativelanguage.googleapis.com/v1beta"

        # Timeout
        timeout_env = os.environ.get("SHADOW_GEMINI_TIMEOUT")
        self.timeout = float(timeout_env) if timeout_env else 30.0

        # Max retries
        retries_env = os.environ.get("SHADOW_GEMINI_MAX_RETRIES")
        self.max_retries = int(retries_env) if retries_env else 3

        # Auto discover
        discover_env = os.environ.get("SHADOW_GEMINI_AUTO_DISCOVER")
        if discover_env is not None:
            self.auto_discover = discover_env.lower() in ("true", "1", "yes")
        else:
            self.auto_discover = True

        # Load local cached models
        self.discovered_models = self._load_cache()

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # gemini-2.5-flash standard pricing: $0.075 / 1M input, $0.30 / 1M output tokens
        return (prompt_tokens * 0.075 / 1_000_000) + (completion_tokens * 0.30 / 1_000_000)

    def _detect_capabilities(self, model_name: str, description: str) -> Dict[str, bool]:
        name_lower = model_name.lower()
        desc_lower = description.lower() if description else ""

        supports_thinking = "thinking" in name_lower or "thinking" in desc_lower
        supports_image = any(x in name_lower for x in ["gemini", "vision", "multimodal"]) or "image" in desc_lower
        supports_tools = any(x in name_lower for x in ["gemini-1.5", "gemini-2.0", "gemini-2.5", "gemini-flash", "gemini-pro"]) or "tool" in desc_lower
        supports_function_calling = supports_tools or "function" in desc_lower
        supports_code_execution = any(x in name_lower for x in ["gemini-1.5", "gemini-2.0", "gemini-2.5", "gemini-flash", "gemini-pro"]) or "code" in desc_lower
        supports_computer_use = "computer" in name_lower or "computer" in desc_lower

        return {
            "supports_thinking": supports_thinking,
            "supports_image": supports_image,
            "supports_tools": supports_tools,
            "supports_function_calling": supports_function_calling,
            "supports_code_execution": supports_code_execution,
            "supports_computer_use": supports_computer_use
        }

    def _save_cache(self, data: Dict[str, Any]):
        try:
            cache_dir = os.path.join(SHADOW_HOME, "cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, "gemini_models.json")
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": time.time(),
                    "models": data
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save Gemini models cache: {e}")

    def _load_cache(self) -> Dict[str, Any]:
        try:
            cache_file = os.path.join(SHADOW_HOME, "cache", "gemini_models.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    # Check age: refresh once every 24 hours
                    age = time.time() - cached.get("timestamp", 0)
                    if age < 24 * 3600:
                        return cached.get("models", {})
        except Exception as e:
            logger.error(f"Failed to load Gemini models cache: {e}")
        return {}

    async def discover_models(self) -> Dict[str, Any]:
        """
        Fetch models from /v1beta/models and cache them.
        """
        if not self.api_key:
            return self.discovered_models or STATIC_FALLBACK_MODELS

        url = f"{self.api_base}/models?key={self.api_key}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    models_list = data.get("models", [])
                    discovered = {}
                    for m in models_list:
                        name = m.get("name", "")
                        short_name = name.split("/")[-1] if "/" in name else name
                        supported_methods = m.get("supportedGenerationMethods", [])

                        if "generateContent" in supported_methods:
                            capabilities = self._detect_capabilities(name, m.get("description", ""))
                            discovered[short_name] = {
                                "name": name,
                                "short_name": short_name,
                                "description": m.get("description", ""),
                                "capabilities": capabilities
                            }

                    if discovered:
                        self._save_cache(discovered)
                        self.discovered_models = discovered
                        return discovered
        except Exception as e:
            log_decision("WARNING", "Gemini model discovery failed", reasoning=str(e))
        return self.discovered_models or STATIC_FALLBACK_MODELS

    def _get_fallback_provider(self):
        config = get_config()
        from shadow.providers.openai import OpenAIProvider
        from shadow.providers.anthropic import AnthropicProvider
        from shadow.providers.mock import MockProvider

        if config.openai.api_key:
            try:
                return OpenAIProvider()
            except Exception:
                pass
        if config.anthropic.api_key:
            try:
                return AnthropicProvider()
            except Exception:
                pass
        return MockProvider()

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            log_decision("WARNING", "Gemini API key is missing", reasoning="Switching to fallback provider.")
            fallback = self._get_fallback_provider()
            return await fallback.chat(messages, **kwargs)

        if self.auto_discover and not self.discovered_models:
            await self.discover_models()

        requested_model = kwargs.get("model") or self.model
        norm_requested_model = requested_model.split("/")[-1] if "/" in requested_model else requested_model

        models_sequence = [norm_requested_model]
        for fallback_model in ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-2.0-flash"]:
            if fallback_model not in models_sequence:
                models_sequence.append(fallback_model)

        known_models = list(self.discovered_models.keys()) if self.discovered_models else list(STATIC_FALLBACK_MODELS.keys())
        for km in known_models:
            if km not in models_sequence:
                models_sequence.append(km)

        last_error = None
        for i, current_norm_model in enumerate(models_sequence):
            if i > 0:
                previous_model = models_sequence[i - 1]
                print(f"Gemini rejected model {previous_model}. Switching to {current_norm_model}...")
                log_decision(
                    "WARNING",
                    "Gemini model fallback",
                    reasoning=f"Model {previous_model} failed (Error: {last_error}). Trying {current_norm_model}."
                )

            current_full_model_id = f"models/{current_norm_model}"
            url = f"{self.api_base}/{current_full_model_id}:generateContent?key={self.api_key}"

            system_instruction = ""
            contents = []
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                else:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}]
                    })

            payload: Dict[str, Any] = {
                "contents": contents,
                "generationConfig": {
                    "temperature": kwargs.get("temperature", 0.7)
                }
            }
            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            backoff = 1.0
            model_failed_fatal = False
            for attempt in range(1, self.max_retries + 1):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            url,
                            json=payload,
                            headers={"Content-Type": "application/json"},
                            timeout=self.timeout
                        )

                        if response.status_code == 200:
                            data = response.json()
                            try:
                                content = data["candidates"][0]["content"]["parts"][0]["text"]
                            except (KeyError, IndexError, TypeError):
                                content = "Empty or filtered response from Gemini model."

                            usage_metadata = data.get("usageMetadata", {})
                            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                            completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
                            total_tokens = usage_metadata.get("totalTokenCount", 0)

                            cost = self.calculate_cost(prompt_tokens, completion_tokens)

                            return {
                                "content": content,
                                "tokens_used": total_tokens,
                                "estimated_cost": cost,
                                "model": current_norm_model
                            }

                        elif response.status_code == 404:
                            last_error = f"404 Not Found: {response.text}"
                            model_failed_fatal = True
                            break

                        elif response.status_code == 429:
                            last_error = f"429 Rate Limit: {response.text}"
                            if attempt < self.max_retries:
                                await asyncio.sleep(backoff)
                                backoff *= 2
                                continue
                            else:
                                break

                        elif response.status_code == 500:
                            last_error = f"500 Server Error: {response.text}"
                            if attempt < self.max_retries:
                                await asyncio.sleep(backoff)
                                backoff *= 2
                                continue
                            else:
                                break
                        else:
                            last_error = f"HTTP Error {response.status_code}: {response.text}"
                            if response.status_code in (400, 401, 403):
                                model_failed_fatal = True
                            break

                except httpx.HTTPError as he:
                    last_error = f"HTTPX Exception: {str(he)}"
                    if attempt < self.max_retries:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        break

            if model_failed_fatal and "key" in last_error.lower():
                break

        print(f"Gemini provider failed completely. Error: {last_error or 'Unknown'}. Temporarily switching provider...")
        log_decision(
            "ERROR",
            "Gemini complete failure",
            reasoning=f"All Gemini models failed. Last error: {last_error}. Switching to temporary fallback provider..."
        )

        fallback_provider = self._get_fallback_provider()
        try:
            return await fallback_provider.chat(messages, **kwargs)
        except Exception as fe:
            from shadow.providers.mock import MockProvider
            mock = MockProvider()
            return await mock.chat(messages, **kwargs)
