import re
from typing import Dict, Any, List, Optional
from shadow.memory.memory import memory_engine
from shadow.core.logging import log_decision

class KnowledgeIndexer:
    @staticmethod
    def clean_and_chunk(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Cleans extra whitespace and chunks markdown/HTML text using a sliding window.
        """
        if not text:
            return []

        # Clean extra newlines and spaces
        cleaned = re.sub(r"\n{3,}", "\n\n", text)
        cleaned = re.sub(r" {2,}", " ", cleaned)

        words = cleaned.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            if i + chunk_size >= len(words):
                break
            i += (chunk_size - overlap)
        return chunks

    async def index_web_context(self, url: str, content: str, workspace: str = "global", title: str = "") -> Dict[str, Any]:
        """
        Clean, chunk, deduplicate and index crawled text directly into Shadow persistent memory.
        """
        chunks = self.clean_and_chunk(content)
        indexed_count = 0

        log_decision("INFO", f"Indexing knowledge context for {url}", reasoning=f"Total content length: {len(content)}, chunks count: {len(chunks)}")

        for idx, chunk in enumerate(chunks):
            # Check for duplicate block in memory first using unique keys
            key = f"web_intel_{url}_{idx}"
            existing = memory_engine.get_memory_by_key(key)
            if existing:
                continue

            # Save to persistent SQLite memory
            memory_engine.save_memory(
                category="insight",
                content=chunk,
                key=key,
                tags=["crawled", "web_intelligence", "knowledge"],
                importance_level="Important",
                workspace=workspace
            )
            indexed_count += 1

        return {
            "success": True,
            "url": url,
            "chunks_processed": len(chunks),
            "new_chunks_indexed": indexed_count,
            "workspace": workspace
        }
