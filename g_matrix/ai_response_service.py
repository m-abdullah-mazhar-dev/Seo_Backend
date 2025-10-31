# services/ai_response_service.py
import requests
from django.conf import settings

class AIResponseService:
    def __init__(self):
        self.api_url = "https://aiapi.appseospider.com/gbp_review_response_gen_bulk"
    
    def generate_responses(self, reviews, business_description="Local HVAC repair and maintenance"):
        """Send reviews to AI API and get responses"""
        if not reviews:
            return []
        
        # Prepare exact payload structure as specified
        payload = {
            "default_business_description": business_description,
            "reviews": [
                {
                    "review_id": review["review_id"],
                    "name": review["name"],
                    "comment": review["comment"],
                    "star_rating": review["star_rating"]
                }
                for review in reviews
            ]
        }
        
        try:
            print(f"📡 Sending {len(reviews)} reviews to AI API...")
            print(f"   API URL: {self.api_url}")
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ AI API Response Status: {response.status_code}")
            print(f"✅ Received {len(result.get('results', []))} AI responses")
            return result.get("results", [])
            
        except requests.exceptions.RequestException as e:
            print(f"❌ AI API error: {e}")
            return self._get_mock_responses(reviews)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return self._get_mock_responses(reviews)
    
    def _get_mock_responses(self, reviews):
        """Generate mock responses when AI API is unavailable"""
        mock_responses = []
        for review in reviews:
            if review["star_rating"] >= 4:
                response_text = f"Thank you, {review['name']}, for your positive feedback! We're delighted to hear about your experience."
            elif review["star_rating"] == 3:
                response_text = f"Thank you for your feedback, {review['name']}. We appreciate your input and will use it to improve our services."
            else:
                response_text = f"Dear {review['name']}, we apologize for the inconvenience. Please contact us directly so we can address your concerns."
            
            mock_responses.append({
                "review_id": review["review_id"],
                "responseText": response_text,
                "policy": "Google Business Profile Response Policy (compliant)",
                "inputs": {
                    "name": review["name"],
                    "comment": review["comment"],
                    "star_rating": review["star_rating"],
                    "sentiment": "positive" if review["star_rating"] >= 4 else "negative" if review["star_rating"] <= 2 else "neutral"
                }
            })
        return mock_responses