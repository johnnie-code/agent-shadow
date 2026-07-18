import asyncio
import re
import urllib.robotparser
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Set, Optional
import httpx
from shadow.core.web.manager import web_provider_manager
from shadow.core.logging import logger, log_decision

class Crawler:
    def __init__(self, depth_limit: int = 3, max_pages: int = 50, rate_limit_delay: float = 1.0):
        self.depth_limit = depth_limit
        self.max_pages = max_pages
        self.rate_limit_delay = rate_limit_delay
        self.visited_urls: Set[str] = set()
        self.robots_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}

    def _get_robots_parser(self, base_url: str) -> urllib.robotparser.RobotFileParser:
        parsed = urlparse(base_url)
        root_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        if root_url in self.robots_parsers:
            return self.robots_parsers[root_url]

        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(root_url)
        try:
            rp.read()
        except Exception:
            # Allow everything on failure to read robots
            pass
        self.robots_parsers[root_url] = rp
        return rp

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        try:
            rp = self._get_robots_parser(url)
            return rp.can_fetch(user_agent, url)
        except Exception:
            return True

    async def crawl(self, start_url: str, **kwargs) -> Dict[str, Any]:
        """
        Recursive crawling with robots.txt awareness, depth limits, sitemap discovery,
        duplicate detection, and rate limiting.
        """
        depth_limit = kwargs.get("depth_limit", self.depth_limit)
        max_pages = kwargs.get("max_pages", self.max_pages)

        queue = [(start_url, 0)]
        results = []

        parsed_start = urlparse(start_url)
        allowed_domain = parsed_start.netloc

        log_decision("INFO", f"Starting crawler on {start_url}", reasoning=f"Max depth: {depth_limit}, Max pages: {max_pages}")

        # Sitemaps parsing attempt
        sitemaps = []
        try:
            rp = self._get_robots_parser(start_url)
            sitemaps = rp.site_maps() or []
        except Exception:
            pass

        while queue and len(results) < max_pages:
            url, depth = queue.pop(0)

            if url in self.visited_urls:
                continue
            self.visited_urls.add(url)

            # Robots.txt validation
            if not self.can_fetch(url):
                logger.warning(f"Robots.txt restricted access to: {url}")
                continue

            # Respect rate limit
            await asyncio.sleep(self.rate_limit_delay)

            # Pick best provider to scrape URL
            provider = web_provider_manager.determine_best_provider("scrape webpage", url)
            try:
                res = await provider.scrape(url)
                if res.get("success"):
                    results.append({
                        "url": url,
                        "depth": depth,
                        "content": res.get("content"),
                        "metadata": res.get("metadata", {})
                    })

                    # Discover links for the next levels
                    if depth < depth_limit:
                        html_content = res.get("html", "")
                        links = self.extract_links(html_content, url, allowed_domain)
                        for link in links:
                            if link not in self.visited_urls:
                                queue.append((link, depth + 1))
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")

        return {
            "success": True,
            "start_url": start_url,
            "pages_crawled": len(results),
            "sitemaps": sitemaps,
            "data": results
        }

    def extract_links(self, html: str, base_url: str, allowed_domain: str) -> List[str]:
        links = []
        if not html:
            return links
        # Basic regex link discovery
        pattern = re.compile(r'href=["\'](https?://[^"\']+|/[^"\']*)["\']', re.IGNORECASE)
        matches = pattern.findall(html)
        for match in matches:
            full_url = urljoin(base_url, match)
            # Standardize / clean URL
            parsed = urlparse(full_url)
            if parsed.netloc == allowed_domain:
                # Remove fragment
                clean_url = parsed._replace(fragment="").geturl()
                links.append(clean_url)
        return list(set(links))
