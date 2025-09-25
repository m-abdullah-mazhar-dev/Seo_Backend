# import requests


# def fetch_closed_deals(access_token, limit=50):
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }

#     deals_url = "https://api.hubapi.com/crm/v3/objects/deals"
#     params = {
#         "properties": "dealname,dealstage,amount,closedate",
#         "associations": "contacts",   # fetch contacts in same response
#         "limit": limit
#     }

#     response = requests.get(deals_url, headers=headers, params=params)
#     if response.status_code != 200:
#         print("Error fetching deals:", response.text)
#         return []

#     deals_data = response.json().get("results", [])
#     closed_deals = []

#     for deal in deals_data:
#         deal_props = deal.get("properties", {})
#         deal_stage = deal_props.get("dealstage")

#         if deal_stage in ["closedwon", "closedlost"]:
#             deal_info = {
#                 "deal_id": deal.get("id"),
#                 "deal_name": deal_props.get("dealname"),
#                 "stage": deal_stage,
#                 "amount": deal_props.get("amount"),
#                 "closedate": deal_props.get("closedate"),
#                 "contacts": []
#             }

#             # ✅ correctly get associated contacts
#             assoc_contacts = (
#                 deal.get("associations", {})
#                     .get("contacts", {})
#                     .get("results", [])
#             )

#             if not assoc_contacts:
#                 print(f"No contacts found for deal {deal.get('id')}")

#             for assoc in assoc_contacts:
#                 contact_id = assoc.get("id")
#                 if not contact_id:
#                     continue

#                 # fetch contact details
#                 contact_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
#                 contact_params = {"properties": "firstname,lastname,email,phone"}
#                 contact_resp = requests.get(contact_url, headers=headers, params=contact_params)

#                 if contact_resp.status_code == 200:
#                     contact_props = contact_resp.json().get("properties", {})
#                     deal_info["contacts"].append({
#                         "firstname": contact_props.get("firstname"),
#                         "lastname": contact_props.get("lastname"),
#                         "email": contact_props.get("email"),
#                         "phone": contact_props.get("phone"),
#                     })
#                 else:
#                     print(f"Error fetching contact {contact_id}: {contact_resp.text}")

#             closed_deals.append(deal_info)

#     return closed_deals


# if __name__ == "__main__":
#     access_token = "CJCit6KVMxIRQlNQMl8kQEwrAgQACAkWPgEYz8-XdCCt_LEnKOOt3QgyFBuX-KyW1m-aPMgbodOTQykJSOm0OhtCU1AyXyRATCsCDgAIGQZxfgE_AQEBAQElAQFCFLZLpOiodwkajZMJLsjrkpr0HRMBSgNuYTJSAFoAYABorfyxJ3AAeAA"
#     deals = fetch_closed_deals(access_token, limit=20)
#     for d in deals:
#         print(d)

# import requests

# # Salesforce OAuth Token URL
# token_url = "https://login.salesforce.com/services/oauth2/token"

# # Refresh Token and Client Credentials (replace with your actual values)

# # Data for refreshing the token
# data = {
#     'grant_type': 'refresh_token',
#     'refresh_token': refresh_token,
#     'client_id': client_id,
#     'client_secret': client_secret
# }

# # Send the request to refresh the token
# response = requests.post(token_url, data=data)

# # Check if the request was successful
# if response.status_code == 200:
#     # Parse the JSON response to get the new access token
#     token_data = response.json()
#     access_token = token_data["access_token"]
#     print(f"New Access Token: {access_token}")
# else:
#     print(f"Error refreshing token: {response.status_code}, {response.text}")



import requests

# Your Salesforce instance URL and new access token
instance_url = "https://orgfarm-d211c8f8aa-dev-ed.develop.my.salesforce.com"
# access_token = "00DgL00000BqV9R!AQEAQMvUPjew1sGM1EyfUP.onAdmmbAXny8zvNjqRS_rhaadEMLTpmEmXUxzYBGpu7FxIqJXFxFmjkXr4m01K.6.2PQnSwHl"  # Use the new access token obtained from refresh

# Salesforce API URL to query Closed Won Opportunities
api_url = f"{instance_url}/services/data/v52.0/query?q=SELECT+Name,+CloseDate,+Amount,+StageName,+Account.Name,+Description,+Owner.Name+FROM+Opportunity"

# Headers for the request, including the Authorization header with Bearer token
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Send GET request to the Salesforce API
response = requests.get(api_url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    opportunities = response.json().get('records', [])
    
    # Print the opportunities' details
    for opp in opportunities:
        print(f"Opportunity Name: {opp['Name']}")
        print(f"Close Date: {opp['CloseDate']}")
        print(f"Amount: {opp['Amount']}")
        print("-" * 50)
else:
    print(f"Error: {response.status_code}, {response.text}")
