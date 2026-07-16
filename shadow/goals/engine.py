import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from shadow.core.database import get_db_connection
from shadow.context.context import context_engine
from shadow.memory.memory import memory_engine

class Goal(BaseModel):
    title: str
    category: str
    priority: str = "Medium"
    dependencies: str = ""
    estimated_completion: str = "TBD"
    confidence: float = 1.0
    status: str = "pending"

class GoalsEngine:
    def parse_mission_markdown(self, markdown_text: str) -> List[Goal]:
        """
        Parse raw markdown text from mission.md.
        - Treat 'Long-Term Goals', 'Current Projects', and 'Skills To Learn' as Goals.
        - Treat other sections (Identity, Core Values, Constraints, Preferences, Habits, Interests) as structured memories.
        """
        goals: List[Goal] = []
        if not markdown_text:
            return goals

        # Regex match headers and their respective text/bullet points
        sections = re.split(r'^#\s+', markdown_text, flags=re.MULTILINE)

        for section in sections:
            if not section.strip():
                continue
            lines = section.split('\n')
            header = lines[0].strip()
            content_lines = [line.strip() for line in lines[1:] if line.strip()]

            # Treat these as Goals
            if header in ["Long-Term Goals", "Current Projects", "Skills To Learn"]:
                category = header
                for line in content_lines:
                    # Look for bullet points
                    if line.startswith("-") or line.startswith("*"):
                        goal_title = line[1:].strip()
                        priority = "High" if any(x in goal_title.lower() for x in ["master", "mext", "elite", "scholarship", "tokyo", "shadow"]) else "Medium"

                        # Check dependencies inside parentheses if any, e.g. "Do X (depends on Y)"
                        deps = ""
                        dep_match = re.search(r'\(depends on ([^\)]+)\)', goal_title, re.IGNORECASE)
                        if dep_match:
                            deps = dep_match.group(1).strip()
                            goal_title = re.sub(r'\(depends on [^\)]+\)', '', goal_title, flags=re.IGNORECASE).strip()

                        goals.append(Goal(
                            title=goal_title,
                            category=category,
                            priority=priority,
                            dependencies=deps,
                            estimated_completion="6 months" if category == "Long-Term Goals" else "3 months",
                            confidence=0.85,
                            status="pending"
                        ))
            else:
                # Treat other sections as structured Memories
                section_content = "\n".join(content_lines)
                if section_content:
                    # Sync to memory DB
                    memory_engine.add_memory(
                        category="preference" if header in ["Preferences", "Constraints", "Core Values"] else "insight",
                        content=section_content,
                        key=f"mission_section_{header.lower().replace(' ', '_')}",
                        tags=["mission", header.lower()]
                    )
        return goals

    def sync_goals_to_db(self, goals: List[Goal]):
        """
        Sync parsed goals to the SQLite database without losing status of existing goals.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        for goal in goals:
            # Check if this goal title already exists in the database
            cursor.execute("SELECT id, status FROM goals WHERE title = ?", (goal.title,))
            row = cursor.fetchone()
            if row:
                # Update but keep the previous status
                cursor.execute("""
                    UPDATE goals
                    SET category = ?, priority = ?, dependencies = ?, estimated_completion = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (goal.category, goal.priority, goal.dependencies, goal.estimated_completion, goal.confidence, row['id']))
            else:
                # Insert new goal
                cursor.execute("""
                    INSERT INTO goals (title, category, priority, dependencies, estimated_completion, confidence, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (goal.title, goal.category, goal.priority, goal.dependencies, goal.estimated_completion, goal.confidence, goal.status))

        conn.commit()
        conn.close()

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """
        Fetch all pending and active goals from the SQLite database.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE status IN ('pending', 'active') ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

# Global Goals Engine singleton
goals_engine = GoalsEngine()
