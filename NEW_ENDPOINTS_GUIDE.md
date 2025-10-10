# New Dynamic Schema & Field Options Endpoints

## Overview

Two new endpoints that dynamically read schema and field options **directly from your Google Sheets data**.

---

## Endpoint 1: Get Schema

### **`GET /api/products/schema`**

Returns all column names present in the actual Google Sheets data.

### Request

```bash
curl http://localhost:8000/api/products/schema
```

### Response

```json
{
  "schema": [
    "id",
    "name",
    "category",
    "brand",
    "price",
    "color",
    "description",
    "image_url",
    "tags"
  ],
  "count": 9
}
```

### Use Cases

- Build dynamic filter forms
- Validate field names before querying
- Display available columns to users
- Generate dropdown menus

---

## Endpoint 2: Get Field Options

### **`GET /api/products/field-options?field={name|index}`**

Returns all unique values for a specific field with counts.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `field` | string | Yes | Column name OR column index (0-8) |
| `category` | string | No | Filter by category first |

### Examples

#### Example 1: Get All Categories

```bash
curl "http://localhost:8000/api/products/field-options?field=category"
```

**Response:**
```json
{
  "field": "category",
  "category_filter": null,
  "options": [
    {"value": "backpack", "count": 10},
    {"value": "car", "count": 10}
  ],
  "total_unique": 2,
  "total_products": 20
}
```

#### Example 2: Get All Brands

```bash
curl "http://localhost:8000/api/products/field-options?field=brand"
```

**Response:**
```json
{
  "field": "brand",
  "category_filter": null,
  "options": [
    {"value": "Adidas", "count": 1},
    {"value": "BMW", "count": 1},
    {"value": "Chevrolet", "count": 1},
    {"value": "Eastpak", "count": 1},
    {"value": "Fjallraven", "count": 1},
    {"value": "Ford", "count": 1},
    ...
  ],
  "total_unique": 20,
  "total_products": 20
}
```

#### Example 3: Get Car Brands Only

```bash
curl "http://localhost:8000/api/products/field-options?field=brand&category=car"
```

**Response:**
```json
{
  "field": "brand",
  "category_filter": "car",
  "options": [
    {"value": "BMW", "count": 1},
    {"value": "Chevrolet", "count": 1},
    {"value": "Ford", "count": 1},
    {"value": "Honda", "count": 1},
    {"value": "Hyundai", "count": 1},
    {"value": "Mazda", "count": 1},
    {"value": "Nissan", "count": 1},
    {"value": "Subaru", "count": 1},
    {"value": "Tesla", "count": 1},
    {"value": "Toyota", "count": 1}
  ],
  "total_unique": 10,
  "total_products": 10
}
```

#### Example 4: Get All Colors

```bash
curl "http://localhost:8000/api/products/field-options?field=color"
```

**Response:**
```json
{
  "field": "color",
  "category_filter": null,
  "options": [
    {"value": "Black", "count": 3},
    {"value": "Blue", "count": 3},
    {"value": "Brown", "count": 1},
    {"value": "Burgundy", "count": 1},
    {"value": "Gray", "count": 3},
    ...
  ],
  "total_unique": 12,
  "total_products": 20
}
```

#### Example 5: Using Column Index

```bash
# Index 2 = category
curl "http://localhost:8000/api/products/field-options?field=2"

# Index 3 = brand
curl "http://localhost:8000/api/products/field-options?field=3"

# Index 5 = color
curl "http://localhost:8000/api/products/field-options?field=5"
```

**Column Index Reference:**
- 0 = id
- 1 = name
- 2 = category
- 3 = brand
- 4 = price
- 5 = color
- 6 = description
- 7 = image_url
- 8 = tags

#### Example 6: Get All Tags (Comma-separated handling)

```bash
curl "http://localhost:8000/api/products/field-options?field=tags"
```

**Response:**
```json
{
  "field": "tags",
  "category_filter": null,
  "options": [
    {"value": "30L", "count": 1},
    {"value": "4x4", "count": 1},
    {"value": "affordable", "count": 2},
    {"value": "autopilot", "count": 1},
    {"value": "awd", "count": 1},
    {"value": "casual", "count": 1},
    ...
  ],
  "total_unique": 45,
  "total_products": 20
}
```

**Note:** Tags are automatically split by commas and counted individually.

---

## Use Cases

### 1. Build Dynamic Filters (Frontend)

```javascript
// Get available categories for dropdown
const schemaRes = await fetch('/api/products/schema');
const { schema } = await schemaRes.json();

// Build filter UI for each field
for (const field of ['category', 'brand', 'color']) {
  const res = await fetch(`/api/products/field-options?field=${field}`);
  const data = await res.json();

  // Create dropdown
  const dropdown = createDropdown(field, data.options);
}
```

### 2. Cascading Filters

```javascript
// Step 1: User selects category
const category = "car";

// Step 2: Get brands for that category only
const res = await fetch(`/api/products/field-options?field=brand&category=${category}`);
const { options } = await res.json();

// Step 3: Show only car brands in dropdown
displayBrands(options);
```

### 3. Chatbot Integration

```javascript
// When user asks "What colors are available for cars?"
const res = await fetch('/api/products/field-options?field=color&category=car');
const { options } = await res.json();

const colors = options.map(opt => opt.value).join(', ');
return `Available colors for cars: ${colors}`;
```

### 4. Price Range Options

```bash
# Get all price points
curl "http://localhost:8000/api/products/field-options?field=price&category=car"
```

Use the min/max to create price range sliders.

---

## Error Handling

### Invalid Field Name

```bash
curl "http://localhost:8000/api/products/field-options?field=invalid"
```

**Response (400):**
```json
{
  "detail": "Field 'invalid' not found. Available fields: id, name, category, brand, price, color, description, image_url, tags"
}
```

### Invalid Column Index

```bash
curl "http://localhost:8000/api/products/field-options?field=99"
```

**Response (400):**
```json
{
  "detail": "Invalid column index. Must be between 0 and 8. Available columns: ['id', 'name', 'category', ...]"
}
```

### No Products Found

```bash
curl "http://localhost:8000/api/products/field-options?field=brand&category=electronics"
```

**Response:**
```json
{
  "field": "brand",
  "category_filter": "electronics",
  "options": [],
  "total_unique": 0,
  "total_products": 0
}
```

---

## Complete Integration Example

### Frontend: Dynamic Filter Builder

```javascript
async function buildFilters() {
  // Get schema
  const schemaRes = await fetch('http://localhost:8000/api/products/schema');
  const { schema } = await schemaRes.json();

  // Build filters for specific fields
  const filterFields = ['category', 'brand', 'color'];

  for (const field of filterFields) {
    const res = await fetch(`http://localhost:8000/api/products/field-options?field=${field}`);
    const data = await res.json();

    console.log(`${field} options:`, data.options);

    // Create HTML dropdown
    const select = document.createElement('select');
    select.name = field;

    data.options.forEach(option => {
      const opt = document.createElement('option');
      opt.value = option.value;
      opt.textContent = `${option.value} (${option.count})`;
      select.appendChild(opt);
    });

    document.getElementById('filters').appendChild(select);
  }
}
```

### Chatbot: Answer Dynamic Questions

```javascript
// User: "What brands of backpacks do you have?"
const category = extractCategory(userMessage); // "backpack"
const field = extractField(userMessage); // "brand"

const res = await fetch(
  `http://localhost:8000/api/products/field-options?field=${field}&category=${category}`
);
const { options } = await res.json();

const brands = options.map(opt => `${opt.value} (${opt.count} products)`).join(', ');
return `We have these backpack brands: ${brands}`;
```

---

## Benefits

✅ **Fully Dynamic** - Reads directly from Google Sheets data
✅ **No Hardcoding** - Schema updates automatically when you add columns
✅ **Filtered Options** - Get options for specific categories
✅ **Count Information** - Know how many products for each option
✅ **Index Support** - Access by column number
✅ **Tags Handling** - Automatically splits comma-separated tags

---

## Testing Checklist

- [ ] Get schema returns all column names
- [ ] Get field options by name works
- [ ] Get field options by index works
- [ ] Category filtering works
- [ ] Tags are split correctly
- [ ] Counts are accurate
- [ ] Empty results handled gracefully
- [ ] Error messages are helpful

---

## Summary

These two endpoints make your API truly dynamic:

1. **`/api/products/schema`** - Discover available fields
2. **`/api/products/field-options`** - Get unique values for any field

No more hardcoding! Everything comes from your actual data! 🎉
