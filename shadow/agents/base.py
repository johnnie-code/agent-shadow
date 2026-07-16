import json
from typing import List, Dict, Any, Optional
from shadow.providers.factory import get_provider
from shadow.tools.registry import tool_registry
from shadow.core.logging import log_decision, logger

class Agent:
    def __init__(self, name: str, role: str, prompt: str, allowed_tools: List[str], provider_name: str = "mock"):
        self.name = name
        self.role = role
        self.prompt = prompt
        self.allowed_tools = allowed_tools
        self.provider = get_provider(provider_name)

    async def execute_instruction(self, instruction: str, context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute a prompt instruction using LLM reasoning and allowed tools.
        """
        tools_info = []
        for t_name in self.allowed_tools:
            tool = tool_registry.get_tool(t_name)
            if tool:
                tools_info.append({
                    "name": tool.name,
                    "description": tool.description,
                    "schema": tool.schema
                })

        system_message = (
            f"You are {self.name}, the {self.role}.\n"
            f"Your Core Directives:\n{self.prompt}\n\n"
            f"Available Tools:\n{json.dumps(tools_info, indent=2)}\n\n"
            f"Unified Workspace Context:\n{json.dumps(context or {}, indent=2)}\n\n"
            "Format your output in valid structured JSON containing 'thought', 'tool_name', 'tool_parameters', and 'result_summary'."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": instruction}
        ]

        try:
            res = await self.provider.chat(messages)
            content = res["content"].strip()

            # Try to decode content as JSON
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                # If mock/raw provider output doesn't match JSON structure, we build a safe fallback dictionary
                payload = {
                    "thought": "Direct model text fallback execution.",
                    "tool_name": None,
                    "tool_parameters": {},
                    "result_summary": content
                }

            tool_name = payload.get("tool_name")
            tool_params = payload.get("tool_parameters", {})
            thought = payload.get("thought", "Analyzing instructions.")

            # Execute tool if resolved and allowed
            if tool_name and tool_name in self.allowed_tools:
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    log_decision(
                        level="INFO",
                        action=f"Agent '{self.name}' executing tool '{tool_name}'",
                        reasoning=thought,
                        provider=self.name
                    )
                    tool_res = await tool.execute(**tool_params)
                    return {
                        "thought": thought,
                        "tool_executed": tool_name,
                        "tool_result": tool_res,
                        "success": tool_res.get("success", False)
                    }

            return {
                "thought": thought,
                "response": payload.get("result_summary", content),
                "success": True
            }
        except Exception as e:
            log_decision(
                level="ERROR",
                action=f"Agent '{self.name}' execution failed",
                reasoning="Exception during prompt execution.",
                error=str(e),
                provider=self.name
            )
            return {"success": False, "error": str(e)}
