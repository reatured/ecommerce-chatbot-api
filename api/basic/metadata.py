"""
Metadata Search Endpoint
Search and retrieve product metadata fields and values
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.services.sheets_client import get_metadata_fields, get_metadata_values

router = APIRouter()


@router.get("/api/metadata")
async def search_metadata(field: Optional[str] = Query(None, description="Metadata field to query (e.g., 'color', 'category')")):
    """
    Search metadata endpoint

    - No parameter: Returns all available metadata field names
    - With field parameter: Returns all values for that field with counts (limit 50)

    Examples:
        GET /api/metadata -> {"fields": ["color", "category", "brand", "tags"]}
        GET /api/metadata?field=color -> {"field": "color", "values": [{"value": "Blue", "count": 10}, ...], "total": 50}
    """
    try:
        # Case 1: No parameter - return all field names
        if not field:
            fields = get_metadata_fields()
            return {"fields": fields}

        # Case 2: With field parameter - return values with counts
        result = get_metadata_values(field, limit=50)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metadata: {str(e)}")
