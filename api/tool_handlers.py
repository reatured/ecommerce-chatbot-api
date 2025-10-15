"""
Tool Handler Functions
----------------------
Implementation functions for Claude tool use.
Each handler corresponds to a tool that Claude can call.
"""

from typing import Dict, Any, List
from api.products import fetch_products_from_sheet, get_unique_categories, get_unique_colors, get_field_metadata


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


def handle_search_products(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for search_products tool

    Searches for products by keyword across multiple fields.

    Args:
        tool_input: Dictionary with 'query' (required) and 'category' (optional)

    Returns:
        Dictionary with matching products
    """
    try:
        query = tool_input.get("query", "").strip()
        category = tool_input.get("category", "").strip()

        if not query or len(query) < 2:
            return {
                "success": False,
                "error": "Query too short",
                "message": "Search query must be at least 2 characters"
            }

        # Fetch all products
        products = fetch_products_from_sheet()

        # Filter by category first if provided
        if category:
            products = [p for p in products if p.get('category', '').lower() == category.lower()]

        # Search in multiple fields
        q_lower = query.lower()
        results = []

        for product in products:
            # Search in name, description, brand, tags, color
            searchable_text = ' '.join([
                product.get('name', ''),
                product.get('description', ''),
                product.get('brand', ''),
                product.get('tags', ''),
                product.get('color', '')
            ]).lower()

            if q_lower in searchable_text:
                results.append(product)

        return {
            "success": True,
            "products": results,
            "count": len(results),
            "query": query,
            "category": category if category else None,
            "message": f"Found {len(results)} products matching '{query}'" + (f" in {category} category" if category else "")
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error searching products: {str(e)}"
        }


def handle_filter_products(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for filter_products tool

    Filters products by category and/or color.

    Args:
        tool_input: Dictionary with 'category' and/or 'color' (optional)

    Returns:
        Dictionary with filtered products
    """
    try:
        category = tool_input.get("category", "").strip()
        color = tool_input.get("color", "").strip()

        # Fetch all products
        products = fetch_products_from_sheet()

        # Apply category filter
        if category:
            products = [p for p in products if p.get('category', '').lower() == category.lower()]

        # Apply color filter
        if color:
            products = [p for p in products if p.get('color', '').lower() == color.lower()]

        filters_applied = []
        if category:
            filters_applied.append(f"category: {category}")
        if color:
            filters_applied.append(f"color: {color}")

        return {
            "success": True,
            "products": products,
            "count": len(products),
            "filters": {
                "category": category if category else None,
                "color": color if color else None
            },
            "message": f"Found {len(products)} products" + (f" with {', '.join(filters_applied)}" if filters_applied else "")
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error filtering products: {str(e)}"
        }


def handle_get_product_details(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for get_product_details tool

    Gets detailed information about a specific product by ID.

    Args:
        tool_input: Dictionary with 'product_id' (required)

    Returns:
        Dictionary with product details
    """
    try:
        product_id = tool_input.get("product_id")

        if product_id is None:
            return {
                "success": False,
                "error": "Missing product_id",
                "message": "Product ID is required"
            }

        # Convert to int if string
        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": "Invalid product_id",
                "message": f"Product ID must be a number, got: {product_id}"
            }

        # Fetch all products
        products = fetch_products_from_sheet()

        # Find product by ID
        product = next((p for p in products if p.get('id') == product_id), None)

        if not product:
            return {
                "success": False,
                "error": "Product not found",
                "message": f"Product with ID {product_id} not found"
            }

        return {
            "success": True,
            "product": product,
            "message": f"Found product: {product.get('name', 'Unknown')}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error getting product details: {str(e)}"
        }


def handle_get_available_colors(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for get_available_colors tool

    Gets all unique colors available in the product database.

    Args:
        tool_input: Dictionary (optional 'category' filter)

    Returns:
        Dictionary with colors list and count
    """
    try:
        category = tool_input.get("category", "").strip()

        # Fetch products from database
        products = fetch_products_from_sheet()

        # Filter by category if provided
        if category:
            products = [p for p in products if p.get('category', '').lower() == category.lower()]

        # Extract unique colors
        colors = get_unique_colors(products)

        return {
            "success": True,
            "colors": colors,
            "count": len(colors),
            "category": category if category else None,
            "message": f"Found {len(colors)} colors" + (f" in {category} category" if category else "") + f": {', '.join(colors)}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error fetching colors: {str(e)}"
        }


def handle_get_field_metadata(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for get_field_metadata tool

    Gets metadata about product fields (brands, tags, etc.).

    Args:
        tool_input: Dictionary with 'field' (optional) and 'category' (optional)

    Returns:
        Dictionary with field metadata
    """
    try:
        field = tool_input.get("field", "").strip()
        category = tool_input.get("category", "").strip()

        # Fetch products from database
        products = fetch_products_from_sheet()

        # Get metadata
        metadata = get_field_metadata(
            products,
            field=field if field else None,
            category_filter=category if category else None
        )

        if field:
            message = f"Found {metadata.get('unique_count', 0)} unique values for '{field}'"
            if category:
                message += f" in {category} category"
        else:
            message = f"Available fields: {', '.join(metadata.get('available_fields', []))}"

        return {
            "success": True,
            "metadata": metadata,
            "message": message
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error getting field metadata: {str(e)}"
        }
