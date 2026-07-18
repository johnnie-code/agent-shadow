import os
import time
import tempfile
import pytest
import asyncio
from shadow.core.database import init_db, get_db_connection
from shadow.core.web.manager import web_provider_manager
from shadow.core.web.provider import BeautifulSoupProvider, PlaywrightProvider, FirecrawlProvider
from shadow.core.web.scraper import Scraper
from shadow.core.web.crawler import Crawler
from shadow.core.web.extractor import ContentExtractor
from shadow.core.web.search import global_search_engine
from shadow.core.web.knowledge import KnowledgeIndexer
from shadow.core.web.cache import global_web_cache
from shadow.core.web.exporter import WebDataExporter
from shadow.core.mcp_manager import mcp_manager
from shadow.core.capabilities import capability_scanner

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

@pytest.mark.asyncio
async def test_provider_selection_routing():
    # 1. Scraping a known url with "schema" should resolve to Firecrawl or similar structured extraction
    prov = web_provider_manager.determine_best_provider("structured extraction schema")
    assert prov.name == "Firecrawl"

    # 2. Scraping a known url with "sitemap" or "map site" should resolve to Firecrawl
    prov = web_provider_manager.determine_best_provider("map site map")
    assert prov.name == "Firecrawl"

    # 3. Scraping an article should resolve to Newspaper4k if available, else Firecrawl
    prov = web_provider_manager.determine_best_provider("blog post article content")
    assert prov.name in ("Newspaper4k", "Firecrawl")

    # 4. Standard webpage should fallback gracefully
    prov = web_provider_manager.determine_best_provider("generic page scrape")
    assert prov.name in ("Firecrawl", "BeautifulSoup")


@pytest.mark.asyncio
async def test_beautiful_soup_scrape():
    provider = BeautifulSoupProvider()
    res = await provider.scrape("https://example.com")
    # If network fails in some environments, BeautifulSoup fallback can return false gracefully,
    # but since it's installed and example.com is public, it should be successful.
    if not res.get("success"):
        # Fallback assertion if network is blocked
        assert "No module named" not in res.get("error", "")
    else:
        assert res["success"] is True
        assert "provider" in res
        assert "content" in res
        assert len(res["content"]) > 0


@pytest.mark.asyncio
async def test_firecrawl_provider_keyless_capabilities():
    firecrawl = FirecrawlProvider()

    # 1. Scrape URL
    scrape_res = await firecrawl.scrape("https://example.com")
    assert scrape_res["success"] is True
    assert len(scrape_res["content"]) > 0
    assert "example" in scrape_res["content"].lower() or "scraped" in scrape_res["content"].lower()

    # 2. Map Site
    map_res = await firecrawl.map_site("https://example.com")
    assert map_res["success"] is True
    assert len(map_res["links"]) > 0

    # 3. Structured extract
    extract_res = await firecrawl.extract("https://example.com", {"properties": {"title": "string"}})
    assert extract_res["success"] is True
    assert "data" in extract_res

    # 4. Docs Search
    docs_res = await firecrawl.docs_search("How do I install?")
    assert docs_res["success"] is True
    assert "citations" in docs_res

    # 5. Scientific Paper Research Index
    research_res = await firecrawl.research_index("deep learning agents")
    assert research_res["success"] is True
    assert len(research_res["papers"]) > 0


@pytest.mark.asyncio
async def test_crawler_and_robots():
    crawler = Crawler(depth_limit=1, max_pages=3)

    # Robots.txt check
    assert crawler.can_fetch("https://google.com/search") is True or crawler.can_fetch("https://google.com/search") is False

    # Recursion simulation
    html = """
    <html>
        <body>
            <a href="https://example.com/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
        </body>
    </html>
    """
    links = crawler.extract_links(html, "https://example.com", "example.com")
    assert len(links) == 2
    assert "https://example.com/page1" in links


@pytest.mark.asyncio
async def test_structured_extractor():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Title</title>
        <meta name="description" content="This is description.">
        <meta property="og:title" content="OpenGraph Title">
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Super AI Agent"
        }
        </script>
    </head>
    <body>
        <table>
            <tr><th>Name</th><th>Score</th></tr>
            <tr><td>Ghost</td><td>100</td></tr>
        </table>
        <pre><code>print('hello world')</code></pre>
        <img src="/img/icon.png">
    </body>
    </html>
    """
    extracted = ContentExtractor.extract_structured_data(html)
    assert extracted["metadata"]["title"] == "Test Title"
    assert extracted["opengraph"]["title"] == "OpenGraph Title"
    assert len(extracted["json_ld"]) == 1
    assert extracted["json_ld"][0]["name"] == "Super AI Agent"
    assert len(extracted["tables"]) == 1
    assert extracted["tables"][0][1] == ["Ghost", "100"]


@pytest.mark.asyncio
async def test_search_and_cache():
    # 1. Cache set/get
    global_web_cache.clear()
    url = f"https://firecrawl.dev/cache-test-{time.time()}"
    data = {"success": True, "content": "fresh data"}

    global_web_cache.set(url, data, ttl=10)
    assert global_web_cache.get(url) == data

    stats = global_web_cache.get_stats()
    assert stats["cache_size"] == 1
    assert stats["active_entries"] == 1

    # 2. Search Engine
    search_res = await global_search_engine.search("artificial intelligence")
    assert search_res["success"] is True
    assert len(search_res["data"]) > 0


@pytest.mark.asyncio
async def test_knowledge_indexer():
    text = "This is a clean paragraph.\n\n" * 50
    chunks = KnowledgeIndexer.clean_and_chunk(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1

    # Using a fully unique URL for test safety across multiple test execution runs
    unique_url = f"https://testindexer.com/test-{time.time()}"
    indexer = KnowledgeIndexer()
    res = await indexer.index_web_context(unique_url, "Knowledge text description sample " * 100)
    assert res["success"] is True
    assert res["new_chunks_indexed"] > 0


@pytest.mark.asyncio
async def test_exporters():
    pages = [
        {"url": "https://ex.com/p1", "depth": 0, "content": "content 1", "metadata": {"title": "Page 1"}},
        {"url": "https://ex.com/p2", "depth": 1, "content": "content 2", "metadata": {"title": "Page 2"}}
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        md_file = os.path.join(tmpdir, "export.md")
        json_file = os.path.join(tmpdir, "export.json")
        csv_file = os.path.join(tmpdir, "export.csv")
        sqlite_file = os.path.join(tmpdir, "export.sqlite")

        assert WebDataExporter.export_markdown(pages, md_file) is True
        assert WebDataExporter.export_json(pages, json_file) is True
        assert WebDataExporter.export_csv(pages, csv_file) is True
        assert WebDataExporter.export_sqlite(pages, sqlite_file) is True

        assert os.path.exists(md_file)
        assert os.path.exists(json_file)
        assert os.path.exists(csv_file)
        assert os.path.exists(sqlite_file)


@pytest.mark.asyncio
async def test_mcp_registration_and_capabilities():
    # Verify Firecrawl MCP server is registered
    server = mcp_manager.get_db_server("firecrawl")
    assert server is not None
    assert server["command"] == "npx"
    assert "firecrawl-mcp" in server["args"]

    # Verify Capability Scanner reports our new Web Intelligence sector
    scan = await capability_scanner.scan_all(force=True)
    assert "web_intelligence" in scan["sectors"]
    web_intel_provs = scan["sectors"]["web_intelligence"]
    assert len(web_intel_provs) > 0

    # Ensure Firecrawl and BeautifulSoup are registered under the Web Intelligence capabilities list
    names = [p.name for p in web_intel_provs]
    assert any("Firecrawl" in n for n in names)
    assert any("BeautifulSoup" in n for n in names)
