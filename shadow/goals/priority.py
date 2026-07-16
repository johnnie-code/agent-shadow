from typing import Dict, Any, List
from shadow.core.database import get_db_connection

class PriorityEngine:
    def calculate_priority_score(
        self,
        impact: float,                    # 1-10
        urgency: float,                   # 1-10
        confidence: float,                # 0-1
        difficulty: float,                # 1-10
        cost: float = 1.0,                # 1-10 (lower cost is better, so we use 11 - cost)
        time_required: float = 2.0,       # 1-10 (shorter is better, so we use 11 - time_required)
        alignment: float = 5.0,           # 1-10
        roi: float = 5.0,                 # Return on investment 1-10
        personal_growth: float = 5.0,     # 1-10
        learning_value: float = 5.0,      # 1-10
        risk: float = 1.0                 # 1-10 (lower risk is better, so we use 11 - risk)
    ) -> float:
        """
        Calculate a multi-factor weighted priority score between 0.0 and 10.0 based on:
        - Impact (10%)
        - Urgency (10%)
        - Confidence (10%)
        - Difficulty (5%)
        - Cost (5%)
        - Time Required (10%)
        - Alignment (20%)
        - ROI (10%)
        - Personal Growth (10%)
        - Learning Value (5%)
        - Risk (5%)
        """
        # Convert cost, risk, and time_required into positive contribution terms where lower is better
        inv_cost = 11.0 - cost
        inv_time = 11.0 - time_required
        inv_risk = 11.0 - risk
        inv_difficulty = 11.0 - difficulty

        # Weighted calculation
        raw_score = (
            (impact * 0.10) +
            (urgency * 0.10) +
            (confidence * 10.0 * 0.10) +
            (inv_difficulty * 0.05) +
            (inv_cost * 0.05) +
            (inv_time * 0.10) +
            (alignment * 0.20) +
            (roi * 0.10) +
            (personal_growth * 0.10) +
            (learning_value * 0.05) +
            (inv_risk * 0.05)
        )

        return max(0.0, min(10.0, round(raw_score, 2)))

    def reprioritize_all_tasks(self):
        """
        Scan all pending tasks in DB and compute dynamically updated weighted scores.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, category FROM tasks WHERE status = 'pending'")
        tasks = cursor.fetchall()

        for task in tasks:
            t_id = task["id"]
            title_lower = task["title"].lower()

            # Default factors
            impact = 5.0
            urgency = 4.0
            confidence = 0.8
            difficulty = 5.0
            cost = 2.0
            time_required = 4.0
            alignment = 5.0
            roi = 5.0
            personal_growth = 5.0
            learning_value = 5.0
            risk = 2.0

            if "mext" in title_lower or "scholarship" in title_lower:
                alignment = 9.5
                impact = 9.5
                urgency = 8.0
                roi = 9.0
                personal_growth = 9.5
                learning_value = 9.0
            elif "japanese" in title_lower or "kanji" in title_lower or "jlpt" in title_lower or "n1" in title_lower:
                alignment = 9.0
                impact = 8.0
                urgency = 6.0
                personal_growth = 9.0
                learning_value = 9.5
            elif "shadow" in title_lower or "agent" in title_lower:
                alignment = 8.5
                impact = 8.0
                urgency = 7.0
                roi = 8.0
                learning_value = 8.5

            score = self.calculate_priority_score(
                impact=impact,
                urgency=urgency,
                confidence=confidence,
                difficulty=difficulty,
                cost=cost,
                time_required=time_required,
                alignment=alignment,
                roi=roi,
                personal_growth=personal_growth,
                learning_value=learning_value,
                risk=risk
            )

            cursor.execute("UPDATE tasks SET priority_score = ? WHERE id = ?", (score, t_id))

        conn.commit()
        conn.close()

# Global Priority Engine singleton
priority_engine = PriorityEngine()
