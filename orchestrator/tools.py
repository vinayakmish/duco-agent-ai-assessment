"""Tool Registry: Tools available to the Planner Agent.

Each tool is a callable that the Planner can invoke during execution.
Tools wrap the underlying agent/parser functions with logging and error handling.
"""
import os
import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("duco_agent.tools")


@dataclass
class ToolResult:
    """Result from a tool invocation."""
    tool_name: str
    success: bool
    result: Any = None
    error: str = ""


class ToolRegistry:
    """Registry of tools available to the Planner Agent."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._descriptions: dict[str, str] = {}
        self._invocation_log: list[dict] = []

    def register(self, name: str, func: Callable, description: str = ""):
        """Register a tool."""
        self._tools[name] = func
        self._descriptions[name] = description
        logger.info(f"Registered tool: {name}")

    def invoke(self, name: str, **kwargs) -> ToolResult:
        """Invoke a tool by name with arguments."""
        if name not in self._tools:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Unknown tool: {name}"
            )

        logger.info(f"Invoking tool: {name}({kwargs})")
        self._invocation_log.append({"tool": name, "args": kwargs, "status": "started"})

        try:
            result = self._tools[name](**kwargs)
            self._invocation_log[-1]["status"] = "success"
            logger.info(f"Tool {name} completed successfully")
            return ToolResult(tool_name=name, success=True, result=result)
        except Exception as e:
            self._invocation_log[-1]["status"] = f"error: {str(e)}"
            logger.error(f"Tool {name} failed: {str(e)}")
            return ToolResult(tool_name=name, success=False, error=str(e))

    def list_tools(self) -> list[dict[str, str]]:
        """List all registered tools with descriptions."""
        return [
            {"name": name, "description": self._descriptions.get(name, "")}
            for name in self._tools
        ]

    def get_invocation_log(self) -> list[dict]:
        """Get the full tool invocation log."""
        return self._invocation_log.copy()
