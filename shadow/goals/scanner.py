import json
from typing import List, Dict, Any
from shadow.core.database import get_db_connection
from shadow.providers.factory import get_provider
from shadow.tools.registry import tool_registry
from shadow.core.logging import log_decision, logger

class OpportunityScanner:
    def __init__(self, provider_name: str = "mock"):
        self.provider = get_provider(provider_name)

    async def scan(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Scan for opportunities using WebSearchTool and aggregate results.
        Analyze results using AI provider to select top structured opportunities.
        """
        search_tool = tool_registry.get_tool("web_search")
        if not search_tool:
            # Re-discover tools if registry empty
            tool_registry.discover_tools()
            search_tool = tool_registry.get_tool("web_search")

        found_items = []
        if search_tool:
            for q in queries:
                res = await search_tool.execute(query=q)
                if res.get("success"):
                    found_items.extend(res["result"])

        if not found_items:
            logger.warning("No raw search items found during opportunity scan.")
            return []

        # Use AI to analyze found items and filter/structure into qualified Opportunity records
        prompt = (
            "You are the Opportunity Agent for PROJECT SHADOW. Your task is to evaluate raw search results and "
            "select high-impact opportunities (scholarships, hackathons, remote jobs, open-source issues, AI news) "
            "that match the user's goals.\n"
            f"Raw Search Results:\n{json.dumps(found_items, indent=2)}\n\n"
            "Respond ONLY with a JSON object matching this schema:\n"
            "{\n"
            '  "opportunities": [\n'
            "    {\n"
            '      "title": "Opportunity Title",\n'
            '      "description": "Short explanation of alignment",\n'
            '      "url": "https://example.com",\n'
            '      "category": "Scholarship" | "Hackathon" | "Remote Job" | "AI News",\n'
            '      "source": "Web Search",\n'
            '      "confidence": 0.95\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        try:
            res = await self.provider.chat([{"role": "system", "content": prompt}])
            data = json.loads(res["content"])
            opportunities = data.get("opportunities", [])

            # Save to Database
            conn = get_db_connection()
            cursor = conn.cursor()
            saved_count = 0
            for opp in opportunities:
                # Avoid duplicates
                cursor.execute("SELECT id FROM opportunities WHERE title = ?", (opp["title"],))
                if cursor.fetchone():
                    continue
                cursor.execute("""
                    INSERT INTO opportunities (title, description, url, category, source, status, confidence)
                    VALUES (?, ?, ?, ?, ?, 'new', ?)
                """, (opp["title"], opp["description"], opp["url"], opp["category"], opp["source"], opp.get("confidence", 1.0)))
                saved_count += 1
            conn.commit()
            conn.close()

            log_decision(
                level="INFO",
                action="Opportunity scan completed",
                reasoning=f"Scanned {len(queries)} queries. Extracted {len(opportunities)} structures.",
                result=f"New opportunities saved to DB: {saved_count}"
            )
            return opportunities
        except Exception as e:
            log_decision(
                level="ERROR",
                action="Opportunity scanning and extraction failed",
                reasoning="Error parsing or communicating with LLM provider.",
                error=str(e)
            )
            return []
