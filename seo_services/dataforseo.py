import requests
import base64
import json

# 🔑 Replace with your actual DataForSEO credentials
LOGIN = "andrius@cdlagency.com"
PASSWORD = "ONBOARDapp10*"

def get_keyword_data(keyword="roof repair nyc", location_name="United States", language_name="English"):
    # Encode login credentials for Basic Auth
    credentials = f"{LOGIN}:{PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()

    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

    payload = [
        {
            "keyword": keyword,
            "location_name": location_name,
            "language_name": language_name
        }
    ]

    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    # Check response
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code, "details": response.text}


# ✅ Example test
if __name__ == "__main__":
    result = get_keyword_data("roof repair nyc")
    print(json.dumps(result, indent=2))
