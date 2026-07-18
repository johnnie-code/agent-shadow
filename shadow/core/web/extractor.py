import re
import json
from typing import Dict, Any, List, Optional

class ContentExtractor:
    @staticmethod
    def extract_structured_data(html: str) -> Dict[str, Any]:
        """
        Robust metadata and structured schema extractor (OpenGraph, JSON-LD, tables, products, etc.)
        """
        if not html:
            return {}

        results = {
            "metadata": {},
            "opengraph": {},
            "json_ld": [],
            "tables": [],
            "code_snippets": [],
            "images": [],
            "links": []
        }

        # 1. Metadata: Title & Meta Description
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            results["metadata"]["title"] = title_match.group(1).strip()

        meta_matches = re.findall(r'<meta\s+name=["\']([^"\']+)["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        for name, content in meta_matches:
            results["metadata"][name.lower()] = content

        # 2. OpenGraph
        og_matches = re.findall(r'<meta\s+property=["\']og:([^"\']+)["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        for prop, content in og_matches:
            results["opengraph"][prop.lower()] = content

        # 3. JSON-LD
        json_ld_blocks = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.IGNORECASE | re.DOTALL)
        for block in json_ld_blocks:
            try:
                data = json.loads(block.strip())
                results["json_ld"].append(data)
            except Exception:
                pass

        # 4. Tables
        table_blocks = re.findall(r'<table[^>]*>(.*?)</table>', html, re.IGNORECASE | re.DOTALL)
        for tbl in table_blocks:
            rows = []
            tr_blocks = re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.IGNORECASE | re.DOTALL)
            for tr in tr_blocks:
                cols = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.IGNORECASE | re.DOTALL)
                clean_cols = [re.sub(r"<[^>]+>", "", col).strip() for col in cols]
                if clean_cols:
                    rows.append(clean_cols)
            if rows:
                results["tables"].append(rows)

        # 5. Code Snippets
        code_blocks = re.findall(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', html, re.IGNORECASE | re.DOTALL)
        if not code_blocks:
            code_blocks = re.findall(r'<code[^>]*>(.*?)</code>', html, re.IGNORECASE | re.DOTALL)
        for cb in code_blocks:
            clean_code = re.sub(r"<[^>]+>", "", cb).strip()
            if len(clean_code) > 15: # avoid tiny inline tags
                results["code_snippets"].append(clean_code)

        # 6. Images
        img_matches = re.findall(r'<img\s+[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        results["images"] = list(set(img_matches))

        # 7. Links
        link_matches = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        results["links"] = list(set(link_matches))

        return results
