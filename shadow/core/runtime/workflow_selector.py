from enum import Enum
from typing import Dict, Any
from shadow.core.runtime.intent_router import IntentClass

class WorkflowType(str, Enum):
    DIRECT_CONVERSATION = "Direct Conversation"
    DIRECT_EXECUTION = "Direct Execution"
    PLAN_AND_EXECUTE = "Plan and Execute"
    PROJECT_TASK_QUEUE = "Project Task Queue"

class WorkflowSelector:
    def __init__(self):
        pass

    def select_workflow(self, text: str, classification: Dict[str, Any]) -> WorkflowType:
        intent = classification.get("intent")
        confidence = classification.get("confidence", 0.0)
        text_lower = text.lower().strip()

        # Simple requests should bypass planning
        # Simple coding requests
        is_simple_coding = intent == IntentClass.CODING and confidence >= 0.7
        is_simple_file = intent == IntentClass.FILE_GENERATION and confidence >= 0.7

        # Check explicit keywords that are simple and shouldn't trigger planning
        simple_keywords = [
            "generate html", "generate python", "write json", "create css",
            "translate text", "summarize document", "explain code", "generate sql",
            "markdown", "regex", "yaml", "csv"
        ]
        has_simple_kw = any(kw in text_lower for kw in simple_keywords)

        if (is_simple_coding or is_simple_file or has_simple_kw) and not any(proj_kw in text_lower for proj_kw in ["build a", "create a complex", "production-ready", "application"]):
            return WorkflowType.DIRECT_EXECUTION

        # Large projects or heavy requests
        project_keywords = [
            "build an android application", "build android", "create a trading platform", "trading platform",
            "research universities", "crawl thousands of pages", "robotics roadmap", "large refactors",
            "autonomous research", "production-ready", "expense tracker"
        ]
        has_project_kw = any(kw in text_lower for kw in project_keywords)
        is_large_intent = intent in (IntentClass.AUTONOMOUS_PROJECT, IntentClass.PLANNING) or has_project_kw

        if is_large_intent:
            return WorkflowType.PROJECT_TASK_QUEUE

        if intent in (IntentClass.CONVERSATION, IntentClass.QUESTION):
            return WorkflowType.DIRECT_CONVERSATION

        # Default fallbacks
        if intent in (IntentClass.RESEARCH, IntentClass.WEB_SEARCH, IntentClass.WEB_CRAWL, IntentClass.MCP, IntentClass.TOOL_EXECUTION, IntentClass.MEMORY):
            return WorkflowType.DIRECT_EXECUTION

        return WorkflowType.PLAN_AND_EXECUTE
