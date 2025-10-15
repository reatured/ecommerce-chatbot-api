"""
Claude Tool Definitions
-----------------------
Defines all tools available to Claude for function calling.
"""

from typing import Dict, Any, List
from api.tool_handlers import (
    handle_get_categories,
    handle_search_products,
    handle_filter_products,
    handle_get_product_details,
    handle_get_available_colors,
    handle_get_field_metadata
)


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


def search_products_tool() -> Dict[str, Any]:
    """
    Tool definition for searching products by keyword

    Returns:
        Tool schema dictionary for Claude API
    """
    return {
        "name": "search_products",
        "description": "Search for products by keyword. Searches across product name, description, brand, tags, and color. CRITICAL: ALWAYS use this tool IMMEDIATELY when user mentions ANY brand name, product type, or specific keyword (e.g., 'BMW', 'Nike', 'laptop', 'sedan'). NEVER suggest or mention specific products without first using this tool to verify they exist in the database. Only present products that are returned in the search results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search keyword or phrase (minimum 2 characters)"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category to limit the search to (e.g., 'car', 'backpack')"
                }
            },
            "required": ["query"]
        }
    }


def filter_products_tool() -> Dict[str, Any]:
    """
    Tool definition for filtering products by category and/or color

    Returns:
        Tool schema dictionary for Claude API
    """
    return {
        "name": "filter_products",
        "description": "Filter products by category and/or color. CRITICAL: ALWAYS use this tool IMMEDIATELY when user mentions a category (e.g., 'car', 'backpack') or color. This returns actual products from the database - ONLY show products that are in the results. Do not suggest products that are not in the returned results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by product category (e.g., 'car', 'backpack', 'electronics')"
                },
                "color": {
                    "type": "string",
                    "description": "Filter by product color (e.g., 'red', 'blue', 'black')"
                }
            },
            "required": []
        }
    }


def get_product_details_tool() -> Dict[str, Any]:
    """
    Tool definition for getting detailed product information by ID

    Returns:
        Tool schema dictionary for Claude API
    """
    return {
        "name": "get_product_details",
        "description": "Get detailed information about a specific product by its ID. Use this when user asks about a specific product or wants more details about a particular item.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "The unique product ID number"
                }
            },
            "required": ["product_id"]
        }
    }


def get_available_colors_tool() -> Dict[str, Any]:
    """
    Tool definition for getting available colors

    Returns:
        Tool schema dictionary for Claude API
    """
    return {
        "name": "get_available_colors",
        "description": "Get all available product colors from the database. Use this when user asks about what colors are available (e.g., 'what colors do you have?', 'show me color options').",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category to limit colors to (e.g., 'car', 'backpack')"
                }
            },
            "required": []
        }
    }


def get_field_metadata_tool() -> Dict[str, Any]:
    """
    Tool definition for getting metadata about product fields

    Returns:
        Tool schema dictionary for Claude API
    """
    return {
        "name": "get_field_metadata",
        "description": "Get metadata about product fields like brands, tags, or other attributes. Use this when user asks about brands, available tags, or wants to know what product attributes are tracked (e.g., 'what brands do you carry?', 'show me all tags').",
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "The product field to analyze (e.g., 'brand', 'tags'). Leave empty to see all available fields."
                },
                "category": {
                    "type": "string",
                    "description": "Optional category to filter products first (e.g., 'car', 'backpack')"
                }
            },
            "required": []
        }
    }


# Tool Registry - maps tool names to handler functions
TOOL_HANDLERS = {
    "get_available_categories": handle_get_categories,
    "search_products": handle_search_products,
    "filter_products": handle_filter_products,
    "get_product_details": handle_get_product_details,
    "get_available_colors": handle_get_available_colors,
    "get_field_metadata": handle_get_field_metadata,
}


def get_all_tools() -> List[Dict[str, Any]]:
    """
    Get all available tool definitions

    Returns:
        List of tool definition dictionaries for Claude API
    """
    return [
        get_available_categories_tool(),
        search_products_tool(),
        filter_products_tool(),
        get_product_details_tool(),
        get_available_colors_tool(),
        get_field_metadata_tool(),
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
