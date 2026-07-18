import asyncio
import time
from typing import Dict, List, Any, Optional, Type
from shadow.providers.base import BaseProvider
from shadow.providers.mock import MockProvider
from shadow.providers.openai import OpenAIProvider
from shadow.providers.anthropic import AnthropicProvider
from shadow.providers.google import GeminiProvider
from shadow.providers.ollama import OllamaProvider
from shadow.core.config import get_config
from shadow.core.logging import log_decision

class ProviderManager:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._metrics: List[Dict[str, Any]] = []
        self._default_provider_name: str = "mock"

        # Register standard/native providers
        self.register_provider("mock", MockProvider())
        self.register_provider("openai", OpenAIProvider())
        self.register_provider("anthropic", AnthropicProvider())
        self.register_provider("google", GeminiProvider())
        self.register_provider("gemini", GeminiProvider())
        self.register_provider("ollama", OllamaProvider())

        # Set default
        config = get_config()
        self._default_provider_name = (config.default_provider or "mock").lower()

    def register_provider(self, name: str, provider: BaseProvider) -> None:
        """Register a new AI provider."""
        self._providers[name.lower()] = provider
        provider.initialize()

    def get_provider(self, name: Optional[str] = None) -> BaseProvider:
        """Get registered provider by name (case-insensitive). Falls back to default."""
        target_name = (name or self._default_provider_name).lower()
        # Handle alternate names
        if target_name == "claude":
            target_name = "anthropic"
        if target_name not in self._providers:
            return self._providers.get("mock") or MockProvider()
        return self._providers[target_name]

    def set_default_provider(self, name: str) -> None:
        """Configure the active default provider."""
        if name.lower() in self._providers:
            self._default_provider_name = name.lower()

    def list_registered_providers(self) -> List[str]:
        return list(self._providers.keys())

    async def health_check_all(self) -> Dict[str, bool]:
        """Check connection health of all registered providers concurrently."""
        results = {}
        tasks = []
        names = []
        for name, provider in self._providers.items():
            # Skip duplicates like google/gemini to avoid double testing
            if name == "google" and "gemini" in results:
                continue
            names.append(name)
            tasks.append(provider.health_check())

        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, res in zip(names, check_results):
            if isinstance(res, Exception):
                results[name] = False
            else:
                results[name] = res
        return results

    def route_provider(self, task_type: str, preference: Optional[str] = None) -> BaseProvider:
        """
        Intelligent provider routing based on task type, latency, cost, and tool support.
        """
        if preference and preference.lower() in self._providers:
            return self.get_provider(preference)

        config = get_config()
        # Default user preference
        user_pref = config.default_provider.lower() if config.default_provider else "mock"

        # Routing rules
        # Simple/Conversation -> Fast local model (Ollama) or fast API (Gemini/Mock)
        if task_type == "conversation":
            if user_pref in ("ollama", "gemini", "mock"):
                return self.get_provider(user_pref)
            return self.get_provider("ollama") if self.get_provider("ollama").supports_streaming() else self.get_provider("mock")

        # Complex coding or high-fidelity tools -> Claude (Anthropic) or OpenAI
        elif task_type in ("coding", "tools", "reasoning"):
            if user_pref in ("anthropic", "openai"):
                return self.get_provider(user_pref)
            # Fallback priority: anthropic -> openai -> gemini -> mock
            for p in ["anthropic", "openai", "gemini"]:
                if p in self._providers:
                    return self._providers[p]

        # Repository analysis or large context -> Gemini (Google) or OpenAI
        elif task_type in ("repo_analysis", "large_context"):
            if user_pref == "gemini" or user_pref == "google":
                return self.get_provider("gemini")
            return self.get_provider("gemini") if "gemini" in self._providers else self.get_provider("openai")

        # Offline Mode -> Ollama or Mock
        elif task_type == "offline":
            return self.get_provider("ollama")

        return self.get_provider()

    async def chat(self, messages: List[Dict[str, str]], task_type: str = "general", provider_override: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Unified chat entrypoint with dynamic routing, automatic fallback, and observability metrics.
        """
        provider = self.route_provider(task_type, provider_override)
        start_time = time.time()

        try:
            res = await provider.chat(messages, **kwargs)
            duration = time.time() - start_time
            self._record_metric(provider.__class__.__name__, duration, res.get("tokens_used", 0), res.get("estimated_cost", 0.0), True)
            return res
        except Exception as e:
            log_decision(
                "WARNING",
                f"Active provider {provider.__class__.__name__} failed during chat",
                reasoning=f"Exception: {e}. Executing automatic fallback..."
            )
            # Automatic Fallback sequence: try each standard provider until one succeeds
            fallbacks = ["gemini", "openai", "ollama", "mock"]
            for fallback_name in fallbacks:
                fallback_prov = self.get_provider(fallback_name)
                if fallback_prov == provider:
                    continue
                try:
                    res = await fallback_prov.chat(messages, **kwargs)
                    duration = time.time() - start_time
                    self._record_metric(fallback_prov.__class__.__name__, duration, res.get("tokens_used", 0), res.get("estimated_cost", 0.0), True)
                    log_decision(
                        "INFO",
                        f"Automatic fallback to {fallback_name} succeeded.",
                        reasoning="Restored conversation/reasoning flow."
                    )
                    return res
                except Exception as fe:
                    logger.warning(f"Fallback to {fallback_name} also failed: {fe}")

            # Safe ultimate Mock fallback if all fails
            mock_prov = self.get_provider("mock")
            res = await mock_prov.chat(messages, **kwargs)
            self._record_metric("MockProvider", time.time() - start_time, res.get("tokens_used", 0), 0.0, False)
            return res

    def _record_metric(self, provider_name: str, duration: float, tokens: int, cost: float, success: bool) -> None:
        self._metrics.append({
            "provider": provider_name,
            "latency": duration,
            "tokens": tokens,
            "cost": cost,
            "success": success,
            "timestamp": time.time()
        })

    def get_metrics_summary(self) -> Dict[str, Any]:
        total_requests = len(self._metrics)
        if total_requests == 0:
            return {"total_requests": 0, "success_rate": 1.0, "total_cost": 0.0, "average_latency": 0.0}

        successes = sum(1 for m in self._metrics if m["success"])
        total_cost = sum(m["cost"] for m in self._metrics)
        total_latency = sum(m["latency"] for m in self._metrics)

        return {
            "total_requests": total_requests,
            "success_rate": successes / total_requests,
            "total_cost": total_cost,
            "average_latency": total_latency / total_requests,
            "metrics": self._metrics[-50:] # Keep latest 50 metrics
        }

    def shutdown(self) -> None:
        for provider in self._providers.values():
            provider.shutdown()

# Global Provider Manager Singleton
provider_manager = ProviderManager()
