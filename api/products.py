"""
Products API - Fetches product data from Google Sheets
"""
import requests
import csv
from io import StringIO
from typing import Optional, List, Dict
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta

router = APIRouter()

# TODO: Replace with your published Google Sheet CSV URL
# Instructions to get this URL:
# 1. Create Google Sheet with columns: id, name, category, brand, price, color, description, image_url, tags
# 2. File → Share → Publish to web → Select "Comma-separated values (.csv)"
# 3. Copy the URL and paste it here
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1xe7ILWQHJZAt0Zs82uuKsd3iKG9ve-fffKqdMrmVMb7i9_JtwWUiaBI1ClTcdQzPQakCVLrw5d1J/pub?gid=0&single=true&output=csv"

# In-memory cache for products
_products_cache = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 300  # 5 minutes cache TTL
}

def fetch_products_from_sheet(use_cache: bool = True) -> List[Dict]:
    """
    Fetch products from published Google Sheet CSV with caching

    Args:
        use_cache: If True, use cached data if available and fresh

    Returns:
        List of product dictionaries
    """
    # Check cache first
    if use_cache and _products_cache["data"] is not None and _products_cache["timestamp"] is not None:
        cache_age = datetime.now() - _products_cache["timestamp"]
        if cache_age.total_seconds() < _products_cache["ttl_seconds"]:
            # Cache is still fresh
            return _products_cache["data"]

    try:
        response = requests.get(CSV_URL, timeout=10)
        response.raise_for_status()

        # Parse CSV
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        products = list(reader)

        # Convert data types
        for product in products:
            # Convert price to float
            try:
                product['price'] = float(product['price'])
            except (ValueError, KeyError):
                product['price'] = 0.0

            # Convert id to int
            try:
                product['id'] = int(product['id'])
            except (ValueError, KeyError):
                product['id'] = 0

        # Update cache
        _products_cache["data"] = products
        _products_cache["timestamp"] = datetime.now()

        return products

    except requests.RequestException as e:
        # Return cached data if available, even if stale
        if _products_cache["data"] is not None:
            print(f"Error fetching products, using cached data: {e}")
            return _products_cache["data"]
        # Return empty list if no cache available
        print(f"Error fetching products: {e}")
        return []
    except Exception as e:
        # Return cached data if available
        if _products_cache["data"] is not None:
            print(f"Error parsing products, using cached data: {e}")
            return _products_cache["data"]
        print(f"Error parsing products: {e}")
        return []


def get_unique_categories(products: List[Dict]) -> List[str]:
    """
    Extract unique categories from products list

    Args:
        products: List of product dictionaries

    Returns:
        List of unique category names (sorted)
    """
    categories = set()
    for product in products:
        category = product.get('category', '').strip()
        if category:
            categories.add(category.lower())
    return sorted(list(categories))


def get_unique_colors(products: List[Dict]) -> List[str]:
    """
    Extract unique colors from products list

    Args:
        products: List of product dictionaries

    Returns:
        List of unique color names (sorted)
    """
    colors = set()
    for product in products:
        color = product.get('color', '').strip()
        if color:
            colors.add(color.lower())
    return sorted(list(colors))


@router.get("/api/products")
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category (car or backpack)"),
    color: Optional[str] = Query(None, description="Filter by color")
):
    """
    Get all products with optional filters

    Query Parameters:
    - category: Filter by category (optional)
    - color: Filter by color (optional)

    Returns:
        JSON with filtered products
    """
    products = fetch_products_from_sheet()

    # Apply category filter
    if category:
        products = [p for p in products if p.get('category', '').lower() == category.lower()]

    # Apply color filter
    if color:
        products = [p for p in products if p.get('color', '').lower() == color.lower()]

    return {
        "products": products,
        "count": len(products),
        "filters": {
            "category": category,
            "color": color
        }
    }


@router.get("/api/products/search")
async def search_products(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Limit search to category")
):
    """
    Search products by keyword

    Searches in: name, description, brand, tags

    Query Parameters:
    - q: Search query (required)
    - category: Optional category filter

    Returns:
        JSON with matching products
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")

    products = fetch_products_from_sheet()

    # Filter by category first if provided
    if category:
        products = [p for p in products if p.get('category', '').lower() == category.lower()]

    # Search in multiple fields
    q_lower = q.lower()
    results = []

    for product in products:
        # Search in name, description, brand, tags
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
        "products": results,
        "count": len(results),
        "query": q,
        "category": category
    }


@router.get("/api/products/{product_id}")
async def get_product_by_id(product_id: int):
    """
    Get a single product by ID

    Path Parameters:
    - product_id: Product ID

    Returns:
        Product object
    """
    products = fetch_products_from_sheet()

    # Find product by ID
    product = next((p for p in products if p.get('id') == product_id), None)

    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

    return product


@router.get("/api/init")
async def initialize_app():
    """
    Initialize the application and wake up backend after inactivity.

    This endpoint:
    1. Activates the backend (useful for Render free tier cold starts)
    2. Fetches and caches product data
    3. Returns available categories for quick action buttons (sorted by product count)
    4. Provides metadata for stage 0 product recommendations

    Returns:
        JSON with initialization data including categories, colors, and metadata

    Response Format:
    {
        "status": "ready",
        "categories": ["car", "backpack"],
        "metadata": {
            "total_products": 50,
            "colors_available": ["red", "blue", "black"],
            "last_updated": "2025-10-10T12:00:00Z"
        }
    }
    """
    try:
        # Fetch products (this will populate cache and wake up backend)
        products = fetch_products_from_sheet(use_cache=False)

        # Count products per category
        category_counts = {}
        for product in products:
            category = product.get('category', '').strip().lower()
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1

        # Sort categories by product count (descending)
        categories = sorted(category_counts.keys(), key=lambda cat: category_counts[cat], reverse=True)

        # Extract unique colors
        colors = get_unique_colors(products)

        # Get cache timestamp for last_updated
        last_updated = _products_cache["timestamp"].isoformat() if _products_cache["timestamp"] else datetime.now().isoformat()

        # Build response
        response = {
            "status": "ready",
            "categories": categories,
            "metadata": {
                "total_products": len(products),
                "colors_available": colors,
                "last_updated": last_updated,
                "cache_ttl_seconds": _products_cache["ttl_seconds"]
            }
        }

        return response

    except Exception as e:
        # Even if there's an error, return a minimal response to allow frontend to function
        print(f"Error in initialization: {e}")
        return {
            "status": "error",
            "categories": ["car", "backpack"],  # Fallback categories
            "metadata": {
                "total_products": 0,
                "colors_available": [],
                "last_updated": datetime.now().isoformat(),
                "error": str(e)
            }
        }
