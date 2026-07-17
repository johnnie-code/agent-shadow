import json
from typing import List, Dict, Any
from shadow.core.database import get_db_connection
from shadow.providers.factory import get_provider
from shadow.core.logging import log_decision

class TaskGenerator:
    def __init__(self, provider_name: str = "mock"):
        self.provider = get_provider(provider_name)

    async def generate_tasks_for_opportunity(self, opportunity_id: int) -> List[Dict[str, Any]]:
        """
        Takes a found opportunity from DB and generates actionable Level 0 or Level 1 tasks to pursue it.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
        opp = cursor.fetchone()
        conn.close()

        if not opp:
            raise ValueError(f"Opportunity ID {opportunity_id} not found in DB.")

        opp_dict = dict(opp)

        prompt = (
            "You are the Task Generator Agent for PROJECT SHADOW. Your goal is to transform a single high-value "
            "opportunity into an actionable, concrete set of step-by-step tasks (researching, writing files, planning coding sessions).\n"
            f"Opportunity Details:\n{json.dumps(opp_dict, indent=2)}\n\n"
            "Generate between 2 and 4 actionable tasks. Define safety levels accurately:\n"
            "- Level 0: Read-only research, summarizing, downloading information.\n"
            "- Level 1: Creating or writing markdown study guides, planning folders, or updating local lists.\n"
            "- Level 2: Highly restricted (approval required).\n\n"
            "Respond ONLY with a JSON object matching this schema:\n"
            "{\n"
            '  "tasks": [\n'
            "    {\n"
            '      "title": "Task title",\n'
            '      "description": "Short action instruction",\n'
            '      "category": "Research" | "Documentation" | "Coding",\n'
            '      "safety_level": 0 | 1,\n'
            '      "priority_score": 8.5\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        try:
            res = await self.provider.chat([{"role": "system", "content": prompt}])
            data = json.loads(res["content"])
            tasks = data.get("tasks", [])

            # Save generated tasks to DB
            conn = get_db_connection()
            cursor = conn.cursor()
            saved_count = 0
            for task in tasks:
                cursor.execute("""
                    INSERT INTO tasks (title, description, category, safety_level, priority_score, opportunity_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """, (task["title"], task["description"], task["category"], task["safety_level"], task["priority_score"], opportunity_id))
                saved_count += 1

            # Update opportunity status to converted
            cursor.execute("UPDATE opportunities SET status = 'converted' WHERE id = ?", (opportunity_id,))
            conn.commit()
            conn.close()

            log_decision(
                level="INFO",
                action="Generated tasks for opportunity",
                reasoning=f"Converted Opportunity #{opportunity_id} into actionable tasks.",
                result=f"Generated tasks inserted: {saved_count}"
            )
            return tasks
        except Exception as e:
            log_decision(
                level="ERROR",
                action="Task generation failed",
                reasoning=f"Error executing LLM logic for Opportunity #{opportunity_id}.",
                error=str(e)
            )
            return []

    async def generate_tasks_from_natural_language(self, user_intent: str) -> List[Dict[str, Any]]:
        """
        Takes a raw user conversational input and dynamically structures it into multiple subtasks,
        milestones, dependencies, priority scores, and safety levels.
        """
        prompt = (
            "You are the Planning Engine Agent for PROJECT SHADOW. Your task is to break down the "
            "following complex user intent into a structured list of actionable, logical subtasks/milestones.\n"
            f"User Intent: \"{user_intent}\"\n\n"
            "Define milestones/subtasks with the following parameters:\n"
            "- safety_level: 0 (read-only research/planning), 1 (local file writing), 2 (remote execution/approval required)\n"
            "- priority_score: 1.0 to 10.0 (where higher is more critical)\n"
            "- estimated_completion: short description (e.g. '1 hour', '2 days')\n"
            "- dependencies: titles of any preceding tasks in the list\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "tasks": [\n'
            "    {\n"
            '      "title": "Subtask Title",\n'
            '      "description": "Short action instruction",\n'
            '      "category": "Research" | "Coding" | "Documentation" | "Deployment",\n'
            '      "safety_level": 0 | 1 | 2,\n'
            '      "priority_score": 8.5,\n'
            '      "estimated_completion": "30 mins",\n'
            '      "dependencies": ""\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        try:
            res = await self.provider.chat([{"role": "system", "content": prompt}])
            data = json.loads(res["content"])
            tasks = data.get("tasks", [])

            conn = get_db_connection()
            cursor = conn.cursor()
            saved_count = 0
            for task in tasks:
                cursor.execute("""
                    INSERT INTO tasks (title, description, category, safety_level, priority_score, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                """, (task["title"], task["description"], task["category"], task["safety_level"], task["priority_score"]))
                saved_count += 1
            conn.commit()
            conn.close()

            log_decision(
                level="INFO",
                action="Conversational planning executed",
                reasoning=f"Simple intent '{user_intent}' was parsed and planned into subtasks.",
                result=f"Tasks generated and saved to database: {saved_count}"
            )
            return tasks
        except Exception as e:
            log_decision(
                level="ERROR",
                action="Conversational planning failed",
                reasoning=f"Could not convert intent '{user_intent}' to tasks.",
                error=str(e)
            )
            return []
