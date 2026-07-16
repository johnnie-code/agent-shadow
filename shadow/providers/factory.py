from typing import Optional
from shadow.core.config import get_config
from shadow.providers.base import BaseProvider
from shadow.providers.openai import OpenAIProvider
from shadow.providers.anthropic import AnthropicProvider
from shadow.providers.google import GeminiProvider
from shadow.providers.mock import MockProvider

def get_provider(provider_name: Optional[str] = None) -> BaseProvider:
    """
    Returns an instance of the configured or requested provider.
    Falls back to MockProvider if provider is missing or requested is 'mock'.
    """
    config = get_config()
    p_name = (provider_name or config.default_provider or "mock").lower()

    if p_name == "openai":
        return OpenAIProvider()
    elif p_name == "anthropic":
        return AnthropicProvider()
    elif p_name == "gemini" or p_name == "google":
        return GeminiProvider()
    else:
        return MockProvider()
