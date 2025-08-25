# utils.py (create this if not exists in your app)
import stripe
from django.conf import settings
import requests
import logging


stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_product_and_price(package, amount_cents, currency="usd", interval="month"):
    # 1. Create Stripe Product
    product = stripe.Product.create(
        name=package.name,
        description=f"{package.name} Subscription Package",
        metadata={
            "package_name": package.name,
            "interval": str(package.interval),
            "service_limit": str(package.service_limit),
            "service_area_limit": str(package.service_area_limit),
            "business_location_limit": str(package.business_location_limit),
            "blog_limit": str(package.blog_limit),
            "keyword_limit": str(package.keyword_limit),
        }
    )

    # 2. Create Stripe Price
    price = stripe.Price.create(
        product=product.id,
        unit_amount=amount_cents,
        currency=currency,
        recurring={"interval": interval},
    )

    return product.id, price.id




logger = logging.getLogger(__name__)

def call_dataforseo_keyword_suggestions(keywords):
    """
    Call DataForSEO API to get keyword suggestions and metrics
    Returns: Dictionary with original keyword as key and suggestions as value
    """
    if not settings.DATAFORSEO_LOGIN or not settings.DATAFORSEO_PASSWORD:
        logger.error("DataForSEO credentials not configured")
        return None
    
    try:
        # Prepare multiple requests - one for each keyword
        tasks = []
        for keyword in keywords:
            tasks.append({
                "keywords": [keyword],
                "location_name": "United States",
                "language_name": "English",
                "include_serp_info": True,
                "depth": 10  # Get more suggestions
            })
        
        # Make the API call
        response = requests.post(
            "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords/live",
            auth=(settings.DATAFORSEO_LOGIN, settings.DATAFORSEO_PASSWORD),
            json=tasks,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = {}
            
            for task in data.get("tasks", []):
                if task.get("status_code") == 20000:  # Success
                    keyword = task.get("data", {}).get("keywords", [""])[0]
                    results[keyword] = task.get("result", [])
            
            return results
        else:
            logger.error(f"DataForSEO API HTTP error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.exception(f"Error calling DataForSEO API: {str(e)}")
        return None

def extract_keyword_suggestions(keyword_data):
    """
    Extract suggested keywords with their metrics from DataForSEO response
    """
    suggestions = []
    
    for item in keyword_data:
        metrics = {
            "keyword": item.get("keyword", ""),
            "search_volume": item.get("search_volume", 0),
            "competition": item.get("competition", 0),
            "cpc": item.get("cpc", 0),
            "rank": None,
            "url_found": None
        }
        
        # Extract ranking info if available
        serp_info = item.get("serp_info", {})
        if serp_info:
            for serp_item in serp_info.get("se_results", []):
                if serp_item.get("type") == "organic" and settings.TARGET_DOMAIN in serp_item.get("url", ""):
                    metrics["rank"] = serp_item.get("rank_absolute", None)
                    metrics["url_found"] = serp_item.get("url", None)
                    break
        
        suggestions.append(metrics)
    
    return suggestions


def find_best_keyword_alternative(suggestions, original_keyword):
    """
    Find the best keyword alternative based on multiple criteria
    """
    if not suggestions:
        return None
    
    # Filter out poor suggestions
    good_suggestions = [
        kw for kw in suggestions 
        if (kw["search_volume"] >= 50 and  # Minimum search volume
            kw["competition"] <= 0.8 and   # Maximum competition
            kw["keyword"] != original_keyword and  # Not the same keyword
            not kw["keyword"].startswith("how to") and  # Avoid question keywords
            not kw["keyword"].startswith("why") and
            len(kw["keyword"]) <= 60)  # Reasonable length
    ]
    
    if not good_suggestions:
        logger.info(f"⚠️ No good alternatives found for '{original_keyword}'")
        return None
    
    # Score each suggestion (customize these weights as needed)
    for kw in good_suggestions:
        # Higher search volume = better
        volume_score = min(kw["search_volume"] / 1000, 1.0)  # Normalize to 0-1
        
        # Lower competition = better  
        competition_score = 1.0 - min(kw["competition"], 1.0)
        
        # Already ranking well = better
        rank_score = 1.0 if kw["rank"] and kw["rank"] <= 10 else 0.5
        
        # Combined score (adjust weights as needed)
        kw["score"] = (volume_score * 0.5 + competition_score * 0.3 + rank_score * 0.2)
    
    # Return the highest scoring suggestion
    return max(good_suggestions, key=lambda x: x["score"])