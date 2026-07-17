import json
import sqlite3
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from shadow.core.database import get_db_connection

class MemoryEngine:
    def add_memory(
        self,
        category: str,
        content: str,
        key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance_level: str = "Recent",
        importance_score: float = 1.0,
        workspace: Optional[str] = "global"
    ) -> int:
        """
        Store a persistent memory block with level and importance score.
        Levels: 'Recent', 'Important', 'Permanent', 'Archived'
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        tags_str = ",".join(tags) if tags else None

        # Calculate dynamic score if not explicitly set
        if importance_score == 1.0:
            importance_score = self._calculate_heuristics_score(content, tags)

        cursor.execute("""
            INSERT INTO memory (category, key, content, tags, importance_level, importance_score, workspace)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (category, key, content, tags_str, importance_level, importance_score, workspace))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def save_memory(
        self,
        category: str,
        content: str,
        key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance_level: str = "Recent",
        importance_score: Optional[float] = None,
        workspace: Optional[str] = "global"
    ) -> int:
        """
        Save a persistent memory block and return its ID.
        """
        if importance_score is None:
            importance_score = self._calculate_heuristics_score(content, tags)
        return self.add_memory(
            category=category,
            content=content,
            key=key,
            tags=tags,
            importance_level=importance_level,
            importance_score=importance_score,
            workspace=workspace
        )

    def _calculate_heuristics_score(self, content: str, tags: Optional[List[str]]) -> float:
        """
        A robust production heuristic to calculate dynamic memory importance score.
        Key terms (e.g. mission, goals, rules, credentials, lessons) raise score.
        """
        score = 1.0
        content_lower = content.lower()

        # Keyword triggers for higher score
        high_value_keywords = ["mission", "goal", "failure", "success", "lesson learned", "priority", "working style", "credential", "api_key"]
        for kw in high_value_keywords:
            if kw in content_lower:
                score += 1.5

        if tags:
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower in ["mission", "priority", "critical", "goal"]:
                    score += 2.0
                elif tag_lower in ["lesson", "reflection"]:
                    score += 1.0

        return round(score, 2)

    def get_memory_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific unique memory configuration/block.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memory WHERE key = ? ORDER BY id DESC LIMIT 1", (key,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def search_memories(self, query: str, workspace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search memory table. Uses a combination of keyword matching and ranking
        (by importance_score, level, and date) to return the most relevant context first.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        like_query = f"%{query}%"

        # Query matching categories, tags, or keys, ordered by importance_score desc then date desc
        if workspace:
            cursor.execute("""
                SELECT * FROM memory
                WHERE (content LIKE ? OR tags LIKE ? OR category LIKE ? OR key LIKE ?)
                  AND importance_level != 'Archived'
                  AND (workspace = ? OR workspace IS NULL OR workspace = 'global' OR workspace = '')
                ORDER BY importance_score DESC, created_at DESC
            """, (like_query, like_query, like_query, like_query, workspace))
        else:
            cursor.execute("""
                SELECT * FROM memory
                WHERE (content LIKE ? OR tags LIKE ? OR category LIKE ? OR key LIKE ?)
                  AND importance_level != 'Archived'
                ORDER BY importance_score DESC, created_at DESC
            """, (like_query, like_query, like_query, like_query))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_memory(
        self,
        query: str,
        workspace: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search memories. If workspace is provided, returns memories scoped to that
        workspace as well as global memories (where workspace is NULL, 'global' or empty).
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        like_query = f"%{query}%"

        if workspace:
            cursor.execute("""
                SELECT * FROM memory
                WHERE (content LIKE ? OR tags LIKE ? OR category LIKE ? OR key LIKE ?)
                  AND importance_level != 'Archived'
                  AND (workspace = ? OR workspace IS NULL OR workspace = 'global' OR workspace = '')
                ORDER BY importance_score DESC, created_at DESC
                LIMIT ?
            """, (like_query, like_query, like_query, like_query, workspace, limit))
        else:
            cursor.execute("""
                SELECT * FROM memory
                WHERE (content LIKE ? OR tags LIKE ? OR category LIKE ? OR key LIKE ?)
                  AND importance_level != 'Archived'
                ORDER BY importance_score DESC, created_at DESC
                LIMIT ?
            """, (like_query, like_query, like_query, like_query, limit))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_memory(self, memory_id: int, **kwargs) -> bool:
        """
        Updates fields of a persistent memory block by ID.
        """
        valid_fields = {"category", "key", "content", "tags", "importance_level", "importance_score", "workspace"}
        update_parts = []
        params = []
        for k, val in kwargs.items():
            if k not in valid_fields:
                raise ValueError(f"Invalid memory field: {k}")
            if k == "tags" and isinstance(val, list):
                val = ",".join(val)
            update_parts.append(f"{k} = ?")
            params.append(val)

        if not update_parts:
            return False

        params.append(memory_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE memory
            SET {", ".join(update_parts)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, params)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_memory(self, memory_id: int) -> bool:
        """
        Deletes a persistent memory block by ID.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def rank_memory(self, memory_id: int, level: str, score: float):
        """
        Explicitly update the ranking/importance parameters of a memory block.
        """
        if level not in ["Recent", "Important", "Permanent", "Archived"]:
            raise ValueError(f"Invalid memory level: {level}")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE memory
            SET importance_level = ?, importance_score = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (level, score, memory_id))
        conn.commit()
        conn.close()

    def retrieve_context(self, query: str, limit: int = 5, workspace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve semantic/ranked memory context for conversational queries.
        Combines relevance of query keywords with memory importance ranking.
        """
        memories = self.search_memories(query, workspace=workspace)
        # Perform scoring refinement: assign extra weight to records that contain specific query words
        query_words = set(query.lower().split())
        scored_memories = []
        for m in memories:
            content_words = m["content"].lower().split()
            overlap = len(query_words.intersection(content_words))

            # Weighted dynamic score
            dynamic_relevance = m["importance_score"] + (overlap * 0.8)

            # Boost based on level
            if m["importance_level"] == "Permanent":
                dynamic_relevance += 2.0
            elif m["importance_level"] == "Important":
                dynamic_relevance += 1.0

            scored_memories.append((dynamic_relevance, m))

        # Sort by relevance
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_memories[:limit]]

    def add_conversation_message(self, session_id: str, role: str, content: str, provider: Optional[str] = None, tokens: int = 0, cost: float = 0.0):
        """
        Store conversation history message.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversation (session_id, role, content, provider, tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, role, content, provider, tokens, cost))
        conn.commit()
        conn.close()

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve history for context.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, provider, tokens, cost, created_at
            FROM conversation
            WHERE session_id = ?
            ORDER BY id ASC LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_conversation(self, session_id: str):
        """
        Clear logs for session.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversation WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def compress_conversation(self, session_id: str, threshold: int = 15):
        """
        Perform automatic conversation memory compression.
        When conversation gets long, summarizes early messages into a system memory block
        and removes raw lines to keep LLM context light and precise.
        """
        history = self.get_conversation_history(session_id, limit=100)
        if len(history) <= threshold:
            return

        # Split conversation to compress
        to_compress = history[:-6]  # keep the last 6 messages intact
        keep_intact = history[-6:]

        # Create compressed summary content
        summary_text = "### Unified Conversation Context Summary\n"
        for msg in to_compress:
            summary_text += f"- **{msg['role'].upper()}**: {msg['content'][:100]}...\n"

        # Delete old messages and save summary as persistent insight
        self.clear_conversation(session_id)

        # Re-insert summary as system context
        self.add_conversation_message(
            session_id=session_id,
            role="system",
            content=f"[AUTONOMOUS COMPRESSION SUMMARY]\nFollowing is the summarized history of prior turns:\n{summary_text}"
        )

        # Restore intact messages
        for msg in keep_intact:
            self.add_conversation_message(
                session_id=session_id,
                role=msg["role"],
                content=msg["content"],
                provider=msg["provider"],
                tokens=msg["tokens"],
                cost=msg["cost"]
            )

    def archive_old_memories(self, days: int = 30):
        """
        Periodically archive old memories to reduce background clutter.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE memory
            SET importance_level = 'Archived'
            WHERE importance_level = 'Recent'
              AND julianday('now') - julianday(created_at) > ?
        """, (days,))
        conn.commit()
        conn.close()

    def _generate_deterministic_summary(self, rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return "No memories found matching the specified criteria."

        summary_lines = [f"Deterministic Summary of {len(rows)} matching memories:"]
        categories = {}
        for r in rows:
            cat = r["category"]
            categories[cat] = categories.get(cat, 0) + 1

        cat_strs = [f"{cat.capitalize()}: {count}" for cat, count in categories.items()]
        summary_lines.append(f"- Category breakdown: {', '.join(cat_strs)}")

        highlights = []
        for r in rows[:3]:
            key_info = f" ({r['key']})" if r.get("key") else ""
            content_preview = r["content"][:60] + "..." if len(r["content"]) > 60 else r["content"]
            highlights.append(f"  * [{r['category'].capitalize()}{key_info}]: {content_preview}")

        if highlights:
            summary_lines.append("- Highlights:")
            summary_lines.extend(highlights)

        if len(rows) > 3:
            summary_lines.append(f"  * ... and {len(rows) - 3} more memories.")

        return "\n".join(summary_lines)

    def summarize_memory(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        workspace: Optional[str] = None
    ) -> str:
        """
        Summarizes matching memories using the active LLM provider or a deterministic fallback.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        query_parts = []
        params = []

        if category:
            query_parts.append("category = ?")
            params.append(category)
        if tags:
            for tag in tags:
                query_parts.append("tags LIKE ?")
                params.append(f"%{tag}%")
        if workspace:
            query_parts.append("(workspace = ? OR workspace IS NULL OR workspace = 'global' OR workspace = '')")
            params.append(workspace)

        where_clause = " AND ".join(query_parts) if query_parts else "1"
        cursor.execute(f"""
            SELECT * FROM memory
            WHERE {where_clause} AND importance_level != 'Archived'
            ORDER BY importance_score DESC, created_at DESC
        """, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if not rows:
            return "No memories found matching the specified criteria."

        mem_texts = [
            f"- [{r['category']}] {r['content']} (Tags: {r['tags']}, Workspace: {r['workspace']})"
            for r in rows
        ]
        text_to_summarize = "\n".join(mem_texts)

        prompt = (
            "You are the Memory Engine Summarizer for PROJECT SHADOW.\n"
            "Please summarize the following persistent memories into a concise, high-level summary paragraph:\n\n"
            f"{text_to_summarize}"
        )

        try:
            from shadow.providers.factory import get_provider
            provider = get_provider()

            async def run_chat():
                res = await provider.chat([{"role": "user", "content": prompt}])
                return res.get("content", "").strip()

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                return self._generate_deterministic_summary(rows)
            else:
                return asyncio.run(run_chat())
        except Exception:
            return self._generate_deterministic_summary(rows)

# Global Memory Singleton
memory_engine = MemoryEngine()
