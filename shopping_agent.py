import os
import json
from typing import List, Dict, Any
import httpx # Using httpx for async requests, install with: pip install httpx
from googleapiclient.errors import HttpError

# Note: googleapiclient doesn't directly support async, so we'll use httpx
# for the actual HTTP call to the REST endpoint. You still need google-api-python-client
# installed for potential future use or other Google APIs, but we won't build the service object here.

class ShoppingAgent:
    def __init__(self):
        # Load credentials from environment variables
        self.search_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        if not self.search_api_key or not self.search_engine_id:
            print("WARNING: GOOGLE_API_KEY or GOOGLE_SEARCH_ENGINE_ID not set in .env file.")
            print("ShoppingAgent will not be able to perform web searches.")
        else:
            print("ShoppingAgent initialized with Google Search credentials.")
        
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def find_options(self, specification: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Takes a product specification and searches the web for purchasing options
        using Google Custom Search JSON API.

        Args:
            specification: A dictionary containing the product details.

        Returns:
            A list of potential shopping options.
        """
        if not self.search_api_key or not self.search_engine_id:
            print("ShoppingAgent: Cannot search, API key or Search Engine ID missing.")
            return []
        
        if not specification or not specification.get("name"):
            return []

        product_name = specification["name"]
        features = specification.get("features", [])
        print(f"ShoppingAgent: Searching Google for options for '{product_name}'...")

        # --- Construct Search Query ---
        query = f"buy {product_name}"
        if features:
            # Add maybe the first couple of features to the query for more specificity
            query += f" {' '.join(features[:2])}"
        print(f"ShoppingAgent: Using search query: '{query}'")

        # --- Prepare API Request --- 
        params = {
            'key': self.search_api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': 5 # Requesting top 5 results, adjust as needed
        }

        # --- Call Google Custom Search API using httpx --- 
        results = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                search_data = response.json()

            # --- Parse Results --- 
            if search_data and 'items' in search_data:
                for item in search_data['items']:
                    results.append({
                        "title": item.get('title', 'No Title'),
                        "link": item.get('link', '#'),
                        "snippet": item.get('snippet', 'No description available.')
                    })
                print(f"ShoppingAgent: Successfully retrieved {len(results)} results from Google.")
            else:
                print(f"ShoppingAgent: No items found in Google Search response for query: '{query}'")

        except httpx.HTTPStatusError as e:
            print(f"ShoppingAgent: HTTP error occurred during Google Search: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
             print(f"ShoppingAgent: Network error occurred during Google Search: {e}")
        except json.JSONDecodeError:
            print(f"ShoppingAgent: Failed to decode JSON response from Google Search.")
        except Exception as e:
            print(f"ShoppingAgent: An unexpected error occurred during Google Search: {e}")
            import traceback
            traceback.print_exc()

        return results 