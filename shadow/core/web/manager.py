import os
from typing import Dict, Any, List, Optional
from shadow.core.web.provider import (
    WebProvider,
    BeautifulSoupProvider,
    PlaywrightProvider,
    TrafilaturaProvider,
    NewspaperProvider,
    Crawl4AIProvider,
    FirecrawlProvider
)
from shadow.core.logging import log_decision, logger

class WebProviderManager:
    def __init__(self):
        self._providers: Dict[str, WebProvider] = {}
        self._default_provider_name = "BeautifulSoup"
        self._initialize_providers()

    def _initialize_providers(self):
        # Register standard implementations
        for prov_cls in [
            BeautifulSoupProvider,
            PlaywrightProvider,
            TrafilaturaProvider,
            NewspaperProvider,
            Crawl4AIProvider,
            FirecrawlProvider
        ]:
            prov_inst = prov_cls()
            self._providers[prov_inst.name.lower()] = prov_inst

        # Firecrawl is primary if key is available or as first-class standard
        if "firecrawl" in self._providers:
            self._default_provider_name = "Firecrawl"

    def register_provider(self, provider: WebProvider):
        self._providers[provider.name.lower()] = provider

    def get_provider(self, name: str) -> Optional[WebProvider]:
        return self._providers.get(name.lower())

    def list_providers(self) -> List[WebProvider]:
        return list(self._providers.values())

    def determine_best_provider(self, task: str, url: Optional[str] = None) -> WebProvider:
        """
        Inspect the request and automatically select the best WebProvider.
        E.g.,
        Question about documentation -> Firecrawl Search
        Known webpage -> Firecrawl Scrape / Newspaper4k
        Entire documentation website -> Firecrawl Crawl
        Need browser interaction -> Playwright or Firecrawl Interact
        Need recurring monitoring -> Firecrawl Monitor
        Scientific papers -> Firecrawl Research Index
        Need to answer Firecrawl implementation questions -> Firecrawl Docs Search
        Need structured extraction -> Firecrawl Extract
        Need a sitemap -> Firecrawl Map
        Need a PDF or DOCX parsed -> Firecrawl Parse
        Need troubleshooting -> Firecrawl Ask
        """
        task_clean = task.lower()

        # If Firecrawl is configured or default, check its specialized routing rules
        firecrawl = self.get_provider("firecrawl")

        if firecrawl:
            # 1. Docs Search / Ask questions
            if "how does firecrawl" in task_clean or "firecrawl implementation" in task_clean:
                log_decision("INFO", "Routed to Firecrawl Docs Search", reasoning="Question references Firecrawl setup/docs")
                return firecrawl

            # 2. PDF / Document Parse
            if "parse" in task_clean or (url and any(url.endswith(ext) for ext in (".pdf", ".docx", ".xlsx", ".doc"))):
                log_decision("INFO", "Routed to Firecrawl Parse", reasoning="Task requires document parsing/OCR")
                return firecrawl

            # 3. Research Index
            if "scientific paper" in task_clean or "research paper" in task_clean or "github issue" in task_clean:
                log_decision("INFO", "Routed to Firecrawl Research Index", reasoning="Task requires scientific research index lookup")
                return firecrawl

            # 4. Monitor
            if "monitor" in task_clean or "notify" in task_clean or "cron" in task_clean or "track page" in task_clean:
                log_decision("INFO", "Routed to Firecrawl Monitor", reasoning="Task implies recurring monitors")
                return firecrawl

            # 5. Browser Interaction
            if "click" in task_clean or "form" in task_clean or "interact" in task_clean or "login" in task_clean:
                # Can use Playwright or Firecrawl Interact; choose Firecrawl as default first-class
                log_decision("INFO", "Routed to Firecrawl Interact", reasoning="Interactive browser sessions required")
                return firecrawl

            # 6. Structured Extract
            if "schema" in task_clean or "structured" in task_clean or "json" in task_clean:
                log_decision("INFO", "Routed to Firecrawl Extract", reasoning="Structured extraction with schema requested")
                return firecrawl

            # 7. Sitemap / Map
            if "sitemap" in task_clean or "map site" in task_clean or "discover urls" in task_clean:
                log_decision("INFO", "Routed to Firecrawl Map", reasoning="Sitemap/Map discovery requested")
                return firecrawl

            # 8. Crawling entire documentation website
            if "crawl" in task_clean or "entire website" in task_clean:
                log_decision("INFO", "Routed to Firecrawl Crawl", reasoning="Large scale crawl task detected")
                return firecrawl

        # Falls back to other providers depending on requested package availability
        playwright = self.get_provider("playwright")
        if playwright and ("screenshot" in task_clean or "javascript" in task_clean or "js rendering" in task_clean):
            log_decision("INFO", "Routed to Playwright", reasoning="Screenshot or heavy JS execution required")
            return playwright

        newspaper = self.get_provider("newspaper4k")
        if newspaper and ("article" in task_clean or "blog post" in task_clean):
            log_decision("INFO", "Routed to Newspaper4k", reasoning="Article structured extraction needed")
            return newspaper

        trafilatura = self.get_provider("trafilatura")
        if trafilatura and "clean markdown" in task_clean:
            log_decision("INFO", "Routed to Trafilatura", reasoning="Optimized text/markdown structure required")
            return trafilatura

        # Standard Default
        primary = self.get_provider(self._default_provider_name)
        if primary:
            return primary
        return BeautifulSoupProvider()

# Global singleton
web_provider_manager = WebProviderManager()
