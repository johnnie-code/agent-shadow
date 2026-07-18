from typing import Optional
from shadow.providers.base import BaseProvider
from shadow.providers.manager import provider_manager

def get_provider(provider_name: Optional[str] = None) -> BaseProvider:
    """
    Returns an instance of the configured or requested provider from ProviderManager.
    Ensures backward compatibility and integrates dependency injection.
    """
    return provider_manager.get_provider(provider_name)
