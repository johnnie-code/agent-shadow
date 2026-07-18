from typing import Dict, Any, Optional
from shadow.core.web.manager import web_provider_manager
from shadow.core.logging import log_decision

class Scraper:
    async def scrape_page(self, url: str, provider_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Scrapes a page using the selected or automatically determined provider.
        """
        if provider_name:
            provider = web_provider_manager.get_provider(provider_name)
            if not provider:
                return {"success": False, "error": f"Requested provider '{provider_name}' not found."}
        else:
            provider = web_provider_manager.determine_best_provider("scrape page", url)

        log_decision("INFO", f"Scraper selected provider: {provider.name}", reasoning=f"URL: {url}")
        return await provider.scrape(url, **kwargs)
