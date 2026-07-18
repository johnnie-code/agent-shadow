from enum import Enum
from typing import Dict, Any, List, Optional
from shadow.core.logging import logger
from shadow.providers.factory import get_provider

class IntentClass(str, Enum):
    CONVERSATION = "Conversation"
    QUESTION = "Question"
    CODING = "Coding"
    FILE_GENERATION = "File Generation"
    RESEARCH = "Research"
    PLANNING = "Planning"
    AUTONOMOUS_PROJECT = "Autonomous Project"
    WEB_SEARCH = "Web Search"
    WEB_CRAWL = "Web Crawl"
    MCP = "MCP"
    TOOL_EXECUTION = "Tool Execution"
    MEMORY = "Memory"
    SYSTEM_COMMAND = "System Command"
    MIXED_INTENT = "Mixed Intent"

class IntentRouter:
    def __init__(self, provider_name: str = "mock"):
        self._provider_name = provider_name

    async def classify_intent(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower().strip()

        # Fast deterministic check first to optimize or fallback
        if not text:
            return {"intent": IntentClass.CONVERSATION, "confidence": 1.0}

        # Basic heuristic mapping to ensure high confidence on direct commands or simple requests
        if text_lower in ["exit", "quit", "bye"]:
            return {"intent": IntentClass.SYSTEM_COMMAND, "confidence": 1.0}

        # Use provider to perform semantic classification
        provider = get_provider(self._provider_name)
        prompt = (
            "You are the Runtime Intent Router for PROJECT SHADOW.\n"
            "Classify the user request into exactly one of the following classes:\n"
            f"{', '.join([c.value for c in IntentClass])}\n\n"
            "Provide your classification as a JSON object with keys 'intent' (string) and 'confidence' (float between 0.0 and 1.0).\n\n"
            "Rules:\n"
            "- Direct, simple requests for code, HTML, script generation should be classified as 'Coding' or 'File Generation'.\n"
            "- Complex requests requiring multiple steps, project builds, multi-file structures, or planning should be 'Autonomous Project' or 'Planning'.\n"
            "- Informational questions should be 'Question'.\n"
            "- Web browsing, queries, crawling should be 'Web Search' or 'Web Crawl'.\n\n"
            f"User input: \"{text}\"\n\n"
            "Output JSON only:"
        )

        try:
            res = await provider.chat([{"role": "system", "content": prompt}])
            import json
            data = json.loads(res["content"])
            intent_val = data.get("intent")
            confidence = float(data.get("confidence", 0.5))

            # Match value with Enum
            matched = None
            for c in IntentClass:
                if intent_val and c.value.lower() == str(intent_val).lower():
                    matched = c
                    break

            if matched is None:
                raise ValueError(f"Invalid or missing intent in parsed LLM response: {intent_val}")

            return {"intent": matched, "confidence": confidence}
        except Exception as e:
            logger.info(f"Using deterministic fallback for intent classification: {e}")
            # Deterministic fallback logic
            if any(kw in text_lower for kw in ["html", "css", "js", "javascript", "python", "script", "code", "programming", "sql", "regex"]):
                return {"intent": IntentClass.CODING, "confidence": 0.8}
            elif any(kw in text_lower for kw in ["search", "google", "find out", "look up"]):
                return {"intent": IntentClass.WEB_SEARCH, "confidence": 0.8}
            elif any(kw in text_lower for kw in ["crawl", "scrape", "extract"]):
                return {"intent": IntentClass.WEB_CRAWL, "confidence": 0.8}
            elif any(kw in text_lower for kw in ["build", "create project", "trading platform", "expense tracker", "application", "complex"]):
                return {"intent": IntentClass.AUTONOMOUS_PROJECT, "confidence": 0.85}
            elif any(kw in text_lower for kw in ["plan", "tasks", "schedule"]):
                return {"intent": IntentClass.PLANNING, "confidence": 0.8}

            return {"intent": IntentClass.CONVERSATION, "confidence": 0.7}
