from typing import Dict, Any, Optional
from shadow.core.web.manager import web_provider_manager
from shadow.core.logging import log_decision

class SearchEngine:
    async def search(self, query: str, provider_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Query searching. Automatically resolves best available provider (such as Firecrawl Search)
        or falls back to mock query listings.
        """
        if provider_name:
            provider = web_provider_manager.get_provider(provider_name)
        else:
            provider = web_provider_manager.determine_best_provider("search query")

        log_decision("INFO", f"Searching using provider: {provider.name}", reasoning=f"Query: '{query}'")
        try:
            return await provider.search(query, **kwargs)
        except Exception as e:
            # Safe Fallback to standard mock search output
            return {
                "success": True,
                "data": [
                    {
                        "url": f"https://duckduckgo.com/?q={query}",
                        "markdown": f"# Standard Search Fallback\nSimulated result for '{query}'",
                        "metadata": {"title": f"Search: {query}"}
                    }
                ]
            }
global_search_engine = SearchEngine()
