"""
Products API - Fetches product data from Google Sheets
"""
import requests
import csv
from io import StringIO
from typing import Optional, List, Dict
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

# TODO: Replace with your published Google Sheet CSV URL
# Instructions to get this URL:
# 1. Create Google Sheet with columns: id, name, category, brand, price, color, description, image_url, tags
# 2. File → Share → Publish to web → Select "Comma-separated values (.csv)"
# 3. Copy the URL and paste it here
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1xe7ILWQHJZAt0Zs82uuKsd3iKG9ve-fffKqdMrmVMb7i9_JtwWUiaBI1ClTcdQzPQakCVLrw5d1J/pub?gid=0&single=true&output=csv"

def fetch_products_from_sheet() -> List[Dict]:
    """
    Fetch products from published Google Sheet CSV

    Returns:
        List of product dictionaries
    """
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

        return products

    except requests.RequestException as e:
        # Return empty list if sheet unavailable
        print(f"Error fetching products: {e}")
        return []
    except Exception as e:
        print(f"Error parsing products: {e}")
        return []


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
