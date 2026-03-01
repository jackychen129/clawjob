"""Tool registry stub for agent tools."""
from typing import Callable, Any


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    async def initialize(self):
        pass

    async def register_tool(self, tool_name: str, tool_func: Callable, description: str = ""):
        self._tools[tool_name] = {"func": tool_func, "description": description}
