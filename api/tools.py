"""
Claude Tool Definitions
-----------------------
Defines all tools available to Claude for function calling.
"""

from typing import Dict, Any, List
from api.tool_handlers import handle_get_categories


# Tool Definitions (following Anthropic's tool use schema)
def get_available_categories_tool() -> Dict[str, Any]:
    """
    Tool definition for getting available product categories

    Returns:
        Tool schema dictionary for Claude API
    """
    return {
        "name": "get_available_categories",
        "description": "Get all available product categories from the database. Use this when the user asks about what categories, types, or kinds of products are available.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }


# Tool Registry - maps tool names to handler functions
TOOL_HANDLERS = {
    "get_available_categories": handle_get_categories,
}


def get_all_tools() -> List[Dict[str, Any]]:
    """
    Get all available tool definitions

    Returns:
        List of tool definition dictionaries for Claude API
    """
    return [
        get_available_categories_tool(),
        # Add more tools here as we expand functionality
    ]


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by name with given input

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool

    Returns:
        Tool execution result

    Raises:
        ValueError: If tool name is not recognized
    """
    if tool_name not in TOOL_HANDLERS:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "message": f"Tool '{tool_name}' is not available"
        }

    try:
        handler = TOOL_HANDLERS[tool_name]
        result = handler(tool_input)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error executing tool '{tool_name}': {str(e)}"
        }
