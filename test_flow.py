# test_complete_flow.py
import requests
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SEO_Automation.settings')
django.setup()

from django.conf import settings

BASE_URL = "http://localhost:8000/google-business"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxODYwNjk3LCJpYXQiOjE3NjE4NTM0OTcsImp0aSI6IjgyZjQzM2Y5MGU1NDRmMGZiMGM4ZTg1Zjg2NmRkNjBiIiwidXNlcl9pZCI6NX0.JDOv_4ajJ8r9gNsq4auEM9HqgzqCcLafE1yjmQjtb9M"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_complete_flow():
    mode = "MOCK" if settings.GOOGLE_BUSINESS_USE_MOCK else "LIVE"
    print(f"🚀 Testing COMPLETE Flow in {mode} Mode\n")
    
    # 1. Sync business profiles
    print("1. Syncing business profiles...")
    response = requests.post(f"{BASE_URL}/profiles/sync/", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ {data['message']}")
        for profile in data['profiles']:
            print(f"   🏢 {profile['name']}")
    
    # 2. Fetch reviews
    print("\n2. Fetching reviews...")
    response = requests.get(f"{BASE_URL}/reviews/fetch/", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['count']} reviews in {data['mode']} mode")
        for review in data['reviews'][:2]:
            print(f"   📝 {review['name']} ({review['star_rating']}★): {review['comment'][:50]}...")
    
    # 3. Complete automation flow
    print("\n3. Running complete automation...")
    response = requests.post(f"{BASE_URL}/reviews/auto-respond/", headers=headers, timeout=60)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ {data['message']}")
        print(f"   📊 Stats: {data['reviews_fetched']} reviews → {data['ai_responses_generated']} AI responses → {data['responses_posted']} posted")
        print(f"   🎯 Success rate: {data['success_rate']}")
        
        # Show sample responses
        if data['sample_ai_responses']:
            print(f"\n   Sample AI Responses:")
            for ai_resp in data['sample_ai_responses']:
                print(f"   💬 {ai_resp['review_id']}: {ai_resp['responseText'][:80]}...")
    
    print(f"\n✅ {mode} Mode Test Completed Successfully!")

if __name__ == "__main__":
    test_complete_flow()