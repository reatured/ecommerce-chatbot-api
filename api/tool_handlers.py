"""
Tool Handler Functions
----------------------
Implementation functions for Claude tool use.
Each handler corresponds to a tool that Claude can call.
"""

from typing import Dict, Any
from api.products import fetch_products_from_sheet, get_unique_categories


def handle_get_categories(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for get_available_categories tool

    Returns all available product categories from the database.

    Args:
        tool_input: Tool input parameters (empty for this tool)

    Returns:
        Dictionary with categories list and count
    """
    try:
        # Fetch products from database
        products = fetch_products_from_sheet()

        # Extract unique categories
        categories = get_unique_categories(products)

        return {
            "success": True,
            "categories": categories,
            "count": len(categories),
            "message": f"Found {len(categories)} categories: {', '.join(categories)}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error fetching categories: {str(e)}"
        }
