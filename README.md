# Shopping Chatbot Frontend

An **AI-powered shopping assistant** that helps users find products through conversation and image search.
---


- **General Conversation** – natural, open-ended chat with a single unified agent  
- **Text-Based Product Recommendation** – e.g., “Recommend me a t-shirt for sports.”  
- **Image-Based Product Search** – upload an image to find visually similar catalog items  

---

## Demo Web Page
👉 [Frontend Demo](https://shop-glass-ai.lovable.app/)  
Try Car and Backpack for now as they have the most data in the database for demo.

👉 [Backend Repo](https://github.com/reatured/ecommerce-chatbot-api)  
👉 [Product Database](https://docs.google.com/spreadsheets/d/1LjQn5xgkAsXlW0kxCfq60C8P_siXzzGksx8LdMOH9YU/edit?usp=sharing)  
_Add more products in any category, and the chatbot automatically adapts its recommendations in real time._

## ⚙️ Tech Stack & Design Decisions

### 🧠 Frontend — React + TypeScript
- Parse structured AI responses and dynamically update UI stages based on parsed metadata  
- Product display panel that renders products from AI response metadata  
- Dynamic data retrieval from the backend database  

### ⚡ Backend — FastAPI (Python)
- **Anthropic AI API** for conversational chatbot and image understanding  
- Tool-use enabled, allowing AI to dynamically read needed categories and options for further conversation  
- Endpoints such as *get all categories* and *get all options* allow AI to quickly fetch necessary info without loading the full database — reducing token cost, data transfer, and latency  
- **Google Sheets (CSV)** as a lightweight, updatable product database  
- Product information updates in real time; since AI reads data dynamically, any database change is immediately reflected  
- Built-in caching and filtering for efficient product queries  

**Why this stack?**  
The **React + FastAPI** setup provides clear separation of concerns — React manages user interaction and state, while FastAPI handles data, logic, and AI requests.  
Both are lightweight, modern, and fast, enabling seamless real-time communication between frontend and backend.



## Screenshots
**Start Page**  
The landing page showcasing entry points to the AI shopping assistant.  
Quick action button above the input field to quickly suggestion actions.
![Start Page](./Image/Start%20Page.jpeg)

**General Chat**  
General chat interface for open-ended shopping questions and guidance.  
![General Chat](./Image/AI%20Shopping%20General%20Chat.jpeg)

**Filter with AI**  
AI-powered product filtering to refine results by attributes and preferences.  
![Filter with AI](./Image/Filter%20with%20AI.png)

**Clarification Questions**  
AI asks clarifying questions to better understand the user’s needs before recommending.  
![Clarification Questions](./Image/Clarification%20questions%20from%20AI%20.png)

**Product Results from Custom Database**  
Products are retrieved from a custom database to ensure accurate, up-to-date results.  
![Product Results](./Image/Product%20queried%20from%20custom%20database.png)

**Product Detail Page**  
Detailed product view including specs, visuals, and purchase actions.  
![Product Detail Page](./Image/Product%20detail%20page.png)

**Product Chat with Quick Buttons**  
Contextual quick action buttons accelerate follow-up requests during product conversations.  
![Product Chat with Quick Buttons](./Image/Product%20Chat%20with%20Quick%20Buttons.png)

**Image Search**  
Upload an image to find visually similar products from the catalog.  
![Image Search](./Image/Image%20Search.png)

**Image Search 2**  
Another example of visual search results returned from an uploaded image.  
![Image Search 2](./Image/Image%20Search%202.png)

---

## Backend API Endpoints

Backend deployed on **Render:**  
🔗 **https://ecommerce-chatbot-api-09va.onrender.com/**  
Testing endpoints: **https://ecommerce-chatbot-api-09va.onrender.com/docs**

---

### 1) Health / Root
- **Route:** `GET /`
- **Description:** Basic health check and endpoint discovery. Returns a list of available routes and notes.
- **Parameters:** none  
- **Sample use (curl):**
	```bash
	GET https://ecommerce-chatbot-api-09va.onrender.com/
	```
- **Sample response:**
	```json
	{
		"status": "ok",
		"message": "E-commerce Chatbot API is running",
		"endpoints": {
			"init": "/api/init",
			"anthropic_chat": "/api/chat/anthropic/stream",
			"products_list": "/api/products?category={category}&color={color}",
			"products_search": "/api/products/search?q={query}",
			"product_by_id": "/api/products/{id}"
		},
		"notes": { ... }
	}
	```

---

### 2) Initialize App
- **Route:** `GET /api/init`
- **Description:** Wake backend specifically for the Render deployment (takes ~30 seconds after inactivity).  
- **Parameters:** none  
- **Sample use (curl):**
	```bash
	GET https://ecommerce-chatbot-api-09va.onrender.com/api/init
	```
- **Sample response:**
	```json
	{
		"status": "ready",
		"categories": ["car", "backpack"],
		"metadata": {
			"total_products": 50,
			"colors_available": ["red","blue","black"],
			"last_updated": "2025-10-10T12:00:00Z",
			"cache_ttl_seconds": 300
		}
	}
	```

---

### 3) List Products
- **Route:** `GET /api/products`
- **Description:** Returns all products with optional filters for `category` and `color`.  
- **Query parameters:**
	- `category` (optional) — Filter by product category (e.g., `car`, `backpack`)
	- `color` (optional) — Filter by color  
- **Sample use (curl):**
	```bash
	GET https://ecommerce-chatbot-api-09va.onrender.com/api/products?category=backpack&color=blue
	```
- **Sample response (truncated):**
	```json
	{
		"products": [
			{
				"id": 1,
				"name": "Blue Hiking Backpack",
				"brand": "TrailCo",
				"price": 79.99,
				"color": "Blue",
				"category": "backpack",
				"description": "A durable hiking backpack...",
				"image_url": "https://...",
				"tags": "hiking,outdoor"
			}
		],
		"count": 1,
		"filters": {"category": "backpack", "color": "blue"}
	}
	```

---

### 4) Search Products
- **Route:** `GET /api/products/search`
- **Description:** Full-text keyword search across `name`, `description`, `brand`, `tags`, and `color`.  
- **Query parameters:**
	- `q` (required) — Search query string (minimum 2 characters)
	- `category` (optional) — Limit search to a specific category  
- **Sample use (curl):**
	```bash
	GET https://ecommerce-chatbot-api-09va.onrender.com/api/products/search?q=waterproof+backpack&category=backpack
	```
- **Sample response (truncated):**
	```json
	{
		"products": [ /* matching product objects */ ],
		"count": 3,
		"query": "waterproof backpack",
		"category": "backpack"
	}
	```

---

### 5) Get Product by ID
- **Route:** `GET /api/products/{product_id}`
- **Description:** Retrieve a single product by its integer ID.  
- **Path parameters:**
	- `product_id` (required) — integer product id  
- **Sample use (curl):**
	```bash
	GET https://ecommerce-chatbot-api-09va.onrender.com/api/products/123
	```
- **Sample response:**
	```json
	{
		"id": 123,
		"name": "Sample Product",
		"brand": "Brand",
		"price": 49.99,
		"color": "black",
		"category": "car",
		"description": "Full product description...",
		"image_url": "https://...",
		"tags": "auto,accessory"
	}
	```

### 6) Chat with Claude
- **Route:** `POST /api/chat/anthropic/stream`
- **Description:** Main chatbot endpoint powered by Claude AI with vision and tool-use capabilities. The chatbot can search, filter, and recommend products with contextual understanding.
- **Content-Type:** `multipart/form-data`  
- **Parameters (Form Data):**
	- `message` *(string, required)* — User’s text query.  
	- `image` *(file, optional)* — Optional product image (JPEG/PNG).  
	- `conversation_history` *(JSON, optional)* — Previous chat messages for context.  
	- `active_filters` *(JSON, optional)* — Product filters like `{"category":"backpack","color":"blue"}`.  
	- `model` *(string, optional)* — Claude model (default: `"claude-3-5-haiku-latest"`).  
	- `max_tokens` *(integer, optional)* — Max tokens for AI output (default: `512`).  
	- `image_media_type` *(string, optional)* — MIME type (default: `"image/jpeg"`).  

- **Sample use (curl):**
	```bash
	# 1. Simple text query
	curl -X POST https://ecommerce-chatbot-api-09va.onrender.com/api/chat/anthropic/stream \
	  -F "message=Show me blue backpacks under $100"

	# 2. With conversation history
	curl -X POST https://ecommerce-chatbot-api-09va.onrender.com/api/chat/anthropic/stream \
	  -F "message=What about red ones?" \
	  -F 'conversation_history=[{"role":"assistant","content":"Hi!"},{"role":"user","content":"Show me backpacks"}]'

	# 3. With active filters
	curl -X POST https://ecommerce-chatbot-api-09va.onrender.com/api/chat/anthropic/stream \
	  -F "message=Show me products" \
	  -F 'active_filters={"category":"backpack","color":"blue"}'

	# 4. With image upload
	curl -X POST https://ecommerce-chatbot-api-09va.onrender.com/api/chat/anthropic/stream \
	  -F "message=Find products similar to this image" \
	  -F "image=@/path/to/product.jpg"
	```

- **Sample response:**
	```json
	{
		"reply": "I found 3 blue backpacks for you...",
		"products": [
			{
				"id": 12,
				"name": "JanSport Right Pack",
				"category": "backpack",
				"brand": "JanSport",
				"price": 45.0,
				"color": "Blue",
				"description": "Classic school backpack with multiple pockets",
				"image_url": "https://...",
				"tags": "school,classic,everyday"
			}
		]
	}
	```

- **Error responses:**
	```json
	{ "detail": "Missing ANTHROPIC_API_KEY" }
	```
	```json
	{ "detail": "Error message from Claude API or processing" }
	```

- **Notes:**
	- Supports **text + image** inputs for product search and recommendations.  
	- Maintains **conversation memory** across sessions.  
	- Automatically applies **active filters** and re-filters results dynamically.  
	- Removes duplicate products and logs all interactions for debugging.





