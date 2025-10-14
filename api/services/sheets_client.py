"""
Google Sheets CSV Client
Fetches product data from Google Sheets public CSV export
"""

import os
import csv
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

CSV_URL = os.getenv("CSV_URL")


def fetch_products() -> List[Dict]:
    """
    Fetch all products from Google Sheets CSV
    Returns list of product dictionaries
    """
    if not CSV_URL:
        raise ValueError("CSV_URL not configured in environment variables")

    try:
        response = requests.get(CSV_URL, timeout=10)
        response.raise_for_status()

        # Parse CSV
        csv_content = response.text
        csv_reader = csv.DictReader(csv_content.splitlines())

        products = []
        for row in csv_reader:
            # Clean and normalize the row data
            product = {
                "id": row.get("id", ""),
                "name": row.get("name", ""),
                "brand": row.get("brand", ""),
                "price": row.get("price", ""),
                "color": row.get("color", ""),
                "category": row.get("category", ""),
                "description": row.get("description", ""),
                "tags": row.get("tags", ""),
                "image_url": row.get("image_url", ""),
                "publish_time": row.get("publish_time", ""),
                "selling_quantity": row.get("selling_quantity", "")
            }
            products.append(product)

        return products

    except requests.RequestException as e:
        raise Exception(f"Failed to fetch CSV data: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing CSV data: {str(e)}")


def get_metadata_fields() -> List[str]:
    """
    Get all available metadata field names
    """
    return ["color", "category", "brand", "tags"]


def get_metadata_values(field: str, limit: int = 50) -> Dict:
    """
    Get all unique values for a specific metadata field with counts

    Args:
        field: The metadata field to query (e.g., 'color', 'category')
        limit: Maximum number of results to return (default 50)

    Returns:
        Dict with field name, values (with counts), and total count
    """
    products = fetch_products()

    # Validate field
    valid_fields = get_metadata_fields()
    if field not in valid_fields:
        raise ValueError(f"Invalid field '{field}'. Valid fields: {valid_fields}")

    # Count occurrences
    value_counts = {}

    for product in products:
        value = product.get(field, "").strip()

        # Handle tags specially (comma-separated)
        if field == "tags" and value:
            tags = [tag.strip() for tag in value.split(",")]
            for tag in tags:
                if tag:
                    value_counts[tag] = value_counts.get(tag, 0) + 1
        elif value:
            value_counts[value] = value_counts.get(value, 0) + 1

    # Sort by count descending, then alphabetically
    sorted_values = sorted(
        value_counts.items(),
        key=lambda x: (-x[1], x[0])
    )

    # Limit results
    limited_values = sorted_values[:limit]

    # Format response
    return {
        "field": field,
        "values": [
            {"value": value, "count": count}
            for value, count in limited_values
        ],
        "total": len(limited_values)
    }
