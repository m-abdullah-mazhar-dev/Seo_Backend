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
import requests

def fetch_solved_deals(oauth_token, limit=50):
    tickets_url = "https://botmeriosupport.zendesk.com/api/v2/tickets.json"
    users_url = "https://botmeriosupport.zendesk.com/api/v2/users/{}"  # for requester email
    
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json"
    }

    params = {
        "status": "solved",  # filter for solved tickets
        "per_page": limit
    }

    try:
        response = requests.get(tickets_url, headers=headers, params=params, timeout=5)
        
        if response.status_code == 200:
            tickets = response.json().get('tickets', [])
            if not tickets:
                print("No solved tickets found.")
                return []

            print(f"Found {len(tickets)} tickets in total.")

            solved_tickets_details = []
            for ticket in tickets:
                if ticket['status'] != 'solved':
                    continue

                # Fetch requester info
                requester_id = ticket.get('requester_id')
                requester_email = None
                if requester_id:
                    user_resp = requests.get(users_url.format(requester_id), headers=headers, timeout=5)
                    if user_resp.status_code == 200:
                        requester_email = user_resp.json()['user'].get('email')

                ticket_info = {
                    "id": ticket['id'],
                    "subject": ticket.get('subject'),
                    "status": ticket.get('status'),
                    "description": ticket.get('description'),
                    "requester_id": requester_id,
                    "requester_email": requester_email,
                    "created_at": ticket.get('created_at'),
                    "updated_at": ticket.get('updated_at'),
                    "priority": ticket.get('priority'),
                    "type": ticket.get('type'),
                }

                solved_tickets_details.append(ticket_info)

                # Print summary
                print(f"\nSolved Ticket ID: {ticket_info['id']}")
                print(f"Subject: {ticket_info['subject']}")
                print(f"Requester Email: {ticket_info['requester_email']}")
                print(f"Description: {ticket_info['description']}")
                print(f"Created At: {ticket_info['created_at']}, Updated At: {ticket_info['updated_at']}")

            return solved_tickets_details
        else:
            print(f"Failed to fetch tickets: {response.status_code} - {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []

# Example Usage


fetch_solved_deals(oauth_token="6f88ef87e9b86b4a164b083f0b0330f6518697a9edee0e6b5fbb2d9a1eb2070e")