import sys
import importlib
import pkgutil
from typing import Dict, List, Type, Optional
from shadow.tools.base import Tool
from shadow.core.logging import logger

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool instance."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: '{tool.name}' (Level {tool.safety_level})")

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def discover_tools(self):
        """
        Dynamically scan shadow.tools package for modules and auto-register tools.
        """
        import shadow.tools
        package = shadow.tools
        prefix = package.__name__ + "."

        for _, module_name, _ in pkgutil.walk_packages(package.__path__, prefix):
            # Avoid re-importing base or registry
            if "base" in module_name or "registry" in module_name:
                continue
            try:
                module = importlib.import_module(module_name)
                # Look for subclasses of Tool (except Tool itself) in the module
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if (
                        isinstance(attribute, type)
                        and issubclass(attribute, Tool)
                        and attribute is not Tool
                    ):
                        tool_instance = attribute()
                        self.register(tool_instance)
            except Exception as e:
                logger.error(f"Error loading tool module {module_name}: {e}")

# Global Tool Registry Singleton
tool_registry = ToolRegistry()
