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

import requests

def get_access_token(client_id, client_secret, authorization_code, redirect_uri):
    subdomain = "botmeriosupport"
    # Replace these with your own values
    token_url = "https://botmeriosupport.zendesk.com/oauth/tokens"  # Replace {subdomain}
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': authorization_code,
        'redirect_uri': redirect_uri,
    }

    response = requests.post(token_url, data=data)

    if response.status_code == 200:
        token_data = response.json()
        print("Access Token:", token_data['access_token'])
    else:
        print(f"Failed to exchange code for token: {response.status_code}, {response.text}")

# Example usage
get_access_token(
    client_id="crm_integration",
    client_secret='0d099f77eeb7bf1eaa59b0cb29a37b9b7d586d90489fd9acadb362ef3db9811d',
    authorization_code='authorization_code_received',
    redirect_uri='https://a92d63f41921.ngrok-free.app/job/crm/oauth/callback/'
)
