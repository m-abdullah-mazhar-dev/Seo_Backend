# import os
# import json
# import requests
# from base64 import b64encode
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# def fetch_keyword_metrics(keywords_list, location_code=2840, language_code="en", debug=True):
#     """
#     Fetch keyword metrics (search_volume, competition, CPC) from DataForSEO Google Ads API.

#     Args:
#         keywords_list (list): List of keywords (strings).
#         location_code (int): DataForSEO location code (default: 2840 = USA).
#         language_code (str): Language code (default: "en").
#         debug (bool): If True, print raw API responses for debugging.

#     Returns:
#         dict: Keywords with search_volume, competition, and CPC.
#     """
#     if not keywords_list or not isinstance(keywords_list, list):
#         raise ValueError("Keywords must be a non-empty list")

#     # Get credentials from .env
#     email = os.getenv("DATAFORSEO_EMAIL")
#     api_key = os.getenv("DATAFORSEO_KEY")

#     if not email or not api_key:
#         raise ValueError("⚠️ DATAFORSEO_EMAIL and DATAFORSEO_KEY must be set in .env")

#     # Encode credentials
#     auth = b64encode(f"{email}:{api_key}".encode()).decode()

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Basic {auth}"
#     }

#     url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

#     # Build payload
#     payload = [{
#         "keywords": keywords_list,
#         "location_code": location_code,
#         "language_code": language_code,
#         "limit": 10,
#     }]

#     all_metrics = {}

#     try:
#         response = requests.post(url, headers=headers, data=json.dumps(payload))
#         response.raise_for_status()
#         data = response.json()

#         # ✅ Debugging raw API response
#         if debug:
#             print("\n====== RAW API RESPONSE ======")
#             print(json.dumps(data, indent=2))
#             print("====== END RAW RESPONSE ======\n")

#         tasks = data.get("tasks", [])
#         if not tasks:
#             print("⚠️ No tasks found in response.")
#             return {}
#         print(f"Task --------- {tasks}")
#         for task in tasks:
#             results = task.get("result", [])
#             if not results:
#                 print("⚠️ No result found in this task:", json.dumps(task, indent=2))
#                 continue

#             # ✅ FIXED: iterate over results directly (no "items")
#             for keyword_info in results:
#                 keyword = keyword_info.get("keyword")
#                 search_volume = keyword_info.get("search_volume")
#                 competition = keyword_info.get("competition_index")  # integer 0-100
#                 cpc = keyword_info.get("cpc")  # CPC in USD

#                 if keyword:
#                     all_metrics[keyword] = {
#                         "search_volume": search_volume,
#                         "competition": competition,
#                         "competition_level": keyword_info.get("competition"),  # e.g., "LOW", "MEDIUM", "HIGH"
#                         "cpc": cpc,
#                         "low_bid": keyword_info.get("low_top_of_page_bid"),
#                         "high_bid": keyword_info.get("high_top_of_page_bid")
#                     }

#     except requests.exceptions.HTTPError as http_err:
#         print("❌ HTTP Error:", response.text)
#         return {"error": f"HTTP error: {http_err}", "details": response.text}
#     except Exception as err:
#         print("❌ Exception:", str(err))
#         return {"error": str(err)}

#     return all_metrics


# if __name__ == "__main__":
#     # Example usage
#     keywords = ["digital marketing", "seo tools"]
#     result = fetch_keyword_metrics(keywords, debug=False)
#     print("\n====== FINAL PARSED RESULT ======")
#     print(json.dumps(result, indent=2))
# # import os
# # import json
# # import requests
# # from base64 import b64encode
# # from dotenv import load_dotenv

# # # Load .env file
# # load_dotenv()

# # CACHE_FILE = "seo_service/keyword_cache.json"   # cache file path

# # def fetch_keyword_suggestions(
# #     keywords_list,
# #     location_code=2840,   # US default
# #     language_code="en",
# #     limit=10,
# #     debug=False,
# #     use_cache=True
# # ):
# #     """
# #     Fetch keyword suggestions from DataForSEO.
# #     Results are cached in a JSON file to avoid repeated API calls.
# #     """

# #     if not keywords_list or not isinstance(keywords_list, list):
# #         raise ValueError("Keywords must be a non-empty list")

# #     # Load cache if available
# #     cache = {}
# #     if use_cache and os.path.exists(CACHE_FILE):
# #         print("exists")
# #         try:
# #             with open(CACHE_FILE, "r", encoding="utf-8") as f:
# #                 cache = json.load(f)
# #                 print("file exist")
# #         except Exception:
# #             cache = {}

# #     # Filter keywords that are already cached
# #     keywords_to_fetch = [kw for kw in keywords_list if kw not in cache]

# #     if debug:
# #         print(f"📂 Cache loaded. Cached keywords: {list(cache.keys())}")
# #         print(f"🔍 Keywords to fetch from API: {keywords_to_fetch}")

# #     # If everything is cached, return from cache
# #     if not keywords_to_fetch:
# #         if debug:
# #             print("✅ Returning results from cache only")
# #         return {kw: cache.get(kw, []) for kw in keywords_list}

# #     # Prepare API credentials
# #     email = os.getenv("DATAFORSEO_EMAIL")
# #     api_key = os.getenv("DATAFORSEO_KEY")

# #     if not email or not api_key:
# #         raise ValueError("Missing DATAFORSEO_EMAIL or DATAFORSEO_KEY in .env")

# #     # Auth headers
# #     auth = b64encode(f"{email}:{api_key}".encode()).decode()
# #     headers = {
# #         "Content-Type": "application/json",
# #         "Authorization": f"Basic {auth}"
# #     }

# #     # url = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live"

# #     # Build payload only for uncached keywords
# #     payload = [{
# #         "keyword": kw,
# #         "location_code": location_code,
# #         "language_code": language_code,
# #         "limit": limit,
# #         "include_clickstream_data": True
# #     } for kw in keywords_to_fetch]

# #     try:
# #         response = requests.post(url, headers=headers, json=payload, timeout=30)
# #         if debug:
# #             print("\n🔹 Request Payload:", json.dumps(payload, indent=2))
# #             print("🔹 Response Status:", response.status_code)
# #             print("🔹 Raw Response Text:", response.text[:500])

# #         response.raise_for_status()
# #         data = response.json()

# #         # Parse API results
# #         for task in data.get("tasks", []):
# #             original = task.get("data", {}).get("keyword")
# #             suggestions = []

# #             results = task.get("result", [])
# #             for res in results:
# #                 items = res.get("items", [])
# #                 for item in items:
# #                     info = item.get("keyword_info_normalized_with_clickstream", {})
# #                     suggestions.append({
# #                         "keyword": item.get("keyword"),
# #                         "search_volume": info.get("search_volume"),
# #                         "competition": info.get("competition"),
# #                         "competition_level": info.get("competition_level"),
# #                         "cpc": info.get("cpc"),
# #                         "low_bid": info.get("low_top_of_page_bid"),
# #                         "high_bid": info.get("high_top_of_page_bid")
# #                     })

# #             # Save new results into cache
# #             cache[original] = suggestions

# #         # Write updated cache back to file
# #         os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
# #         with open(CACHE_FILE, "w", encoding="utf-8") as f:
# #             json.dump(cache, f, indent=2, ensure_ascii=False)

# #         if debug:
# #             print("\n✅ Cache updated & saved.")

# #         # Return results for requested keywords (mix cache + new)
# #         return {kw: cache.get(kw, []) for kw in keywords_list}

# #     except Exception as e:
# #         print(f"❌ Error fetching suggestions: {e}")
# #         # Return whatever cache we have instead of failing completely
# #         return {kw: cache.get(kw, []) for kw in keywords_list}


# # # --------------------------
# # # Example usage:
# # # --------------------------
# # if __name__ == "__main__":
# #     test_keywords = ["seo services", "digital marketing", "content marketing"]
# #     results = fetch_keyword_suggestions(test_keywords, debug=True)
# #     print("\n🎯 Final Results:")
# #     print(json.dumps(results, indent=2))


# utils/dataforseo_utils.py
import os
import json
import requests
import logging
from base64 import b64encode
from django.conf import settings

logger = logging.getLogger(__name__)
# utils/dataforseo_utils.py
def fetch_keyword_suggestions(keywords_list, location_code=2840, language_code="en", limit=10, debug=False):
    """
    Fetch keyword suggestions from DataForSEO API (Function A)
    Returns suggestions with search_volume (but other metrics might be null)
    """
    if not keywords_list or not isinstance(keywords_list, list):
        raise ValueError("Keywords must be a non-empty list")

    email = settings.DATAFORSEO_EMAIL
    api_key = settings.DATAFORSEO_KEY

    if not email or not api_key:
        raise ValueError("DATAFORSEO_EMAIL and DATAFORSEO_KEY must be set in settings")

    auth = b64encode(f"{email}:{api_key}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth}"
    }

    url = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live"

    payload = [{
        "keyword": kw,
        "location_code": location_code,
        "language_code": language_code,
        "limit": limit,
        "include_clickstream_data": True
    } for kw in keywords_list]

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if debug:
            logger.debug(f"Suggestions API Request: {json.dumps(payload, indent=2)}")
            logger.debug(f"Suggestions API Response Status: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        result = {}
        for task in data.get("tasks", []):
            # Check if task was successful
            if task.get("status_code") != 20000:
                logger.warning(f"Task failed: {task.get('status_message')}")
                continue
                
            original = task.get("data", {}).get("keyword")
            if not original:
                continue
                
            suggestions = []
            results = task.get("result", [])
            
            for res in results:
                # Handle different response structures
                items = res.get("items", [])
                if not items:
                    # Try alternative structure
                    keyword_data = res.get("keyword_data", {})
                    if keyword_data:
                        items = [keyword_data]
                
                for item in items:
                    # Extract keyword info from different possible locations
                    keyword_text = item.get("keyword")
                    if not keyword_text:
                        continue
                        
                    # Try to get metrics from different possible locations
                    search_volume = (
                        item.get("search_volume") or 
                        item.get("keyword_info", {}).get("search_volume") or
                        item.get("keyword_info_normalized_with_clickstream", {}).get("search_volume") or
                        0
                    )
                    
                    suggestions.append({
                        "keyword": keyword_text,
                        "search_volume": search_volume,
                        "competition": item.get("competition"),
                        "competition_level": item.get("competition_level"),
                        "cpc": item.get("cpc"),
                        "low_bid": item.get("low_top_of_page_bid"),
                        "high_bid": item.get("high_top_of_page_bid")
                    })

            result[original] = suggestions

        return result

    except Exception as e:
        logger.error(f"Error fetching keyword suggestions: {str(e)}")
        # Return empty dict instead of failing completely
        return {}

def fetch_keyword_metrics(keywords_list, location_code=2840, language_code="en", debug=False):
    """
    Fetch detailed keyword metrics from DataForSEO API (Function B)
    Returns complete metrics including search_volume, competition, CPC
    """
    if not keywords_list or not isinstance(keywords_list, list):
        raise ValueError("Keywords must be a non-empty list")

    email = settings.DATAFORSEO_EMAIL
    api_key = settings.DATAFORSEO_KEY

    if not email or not api_key:
        raise ValueError("DATAFORSEO_EMAIL and DATAFORSEO_KEY must be set in settings")

    auth = b64encode(f"{email}:{api_key}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth}"
    }

    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

    payload = [{
        "keywords": keywords_list,
        "location_code": location_code,
        "language_code": language_code
    }]

    all_metrics = {}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if debug:
            logger.debug(f"Metrics API Request: {json.dumps(payload, indent=2)}")

        response.raise_for_status()
        data = response.json()

        tasks = data.get("tasks", [])
        if not tasks:
            logger.warning("No tasks found in metrics API response")
            return {}

        for task in tasks:
            results = task.get("result", [])
            for keyword_info in results:
                keyword = keyword_info.get("keyword")
                search_volume = keyword_info.get("search_volume", 0)
                competition = keyword_info.get("competition_index", 0)
                cpc = keyword_info.get("cpc", 0)

                if keyword:
                    all_metrics[keyword] = {
                        "search_volume": search_volume,
                        "competition": competition,
                        "competition_level": keyword_info.get("competition"),
                        "cpc": cpc,
                        "low_bid": keyword_info.get("low_top_of_page_bid"),
                        "high_bid": keyword_info.get("high_top_of_page_bid")
                    }

        return all_metrics

    except Exception as e:
        logger.error(f"Error fetching keyword metrics: {str(e)}")
        return {}


