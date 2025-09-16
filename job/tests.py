import requests


def fetch_closed_deals(access_token, limit=50):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    deals_url = "https://api.hubapi.com/crm/v3/objects/deals"
    params = {
        "properties": "dealname,dealstage,amount,closedate",
        "associations": "contacts",   # fetch contacts in same response
        "limit": limit
    }

    response = requests.get(deals_url, headers=headers, params=params)
    if response.status_code != 200:
        print("Error fetching deals:", response.text)
        return []

    deals_data = response.json().get("results", [])
    closed_deals = []

    for deal in deals_data:
        deal_props = deal.get("properties", {})
        deal_stage = deal_props.get("dealstage")

        if deal_stage in ["closedwon", "closedlost"]:
            deal_info = {
                "deal_id": deal.get("id"),
                "deal_name": deal_props.get("dealname"),
                "stage": deal_stage,
                "amount": deal_props.get("amount"),
                "closedate": deal_props.get("closedate"),
                "contacts": []
            }

            # ✅ correctly get associated contacts
            assoc_contacts = (
                deal.get("associations", {})
                    .get("contacts", {})
                    .get("results", [])
            )

            if not assoc_contacts:
                print(f"No contacts found for deal {deal.get('id')}")

            for assoc in assoc_contacts:
                contact_id = assoc.get("id")
                if not contact_id:
                    continue

                # fetch contact details
                contact_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
                contact_params = {"properties": "firstname,lastname,email,phone"}
                contact_resp = requests.get(contact_url, headers=headers, params=contact_params)

                if contact_resp.status_code == 200:
                    contact_props = contact_resp.json().get("properties", {})
                    deal_info["contacts"].append({
                        "firstname": contact_props.get("firstname"),
                        "lastname": contact_props.get("lastname"),
                        "email": contact_props.get("email"),
                        "phone": contact_props.get("phone"),
                    })
                else:
                    print(f"Error fetching contact {contact_id}: {contact_resp.text}")

            closed_deals.append(deal_info)

    return closed_deals


if __name__ == "__main__":
    access_token = "CJCit6KVMxIRQlNQMl8kQEwrAgQACAkWPgEYz8-XdCCt_LEnKOOt3QgyFBuX-KyW1m-aPMgbodOTQykJSOm0OhtCU1AyXyRATCsCDgAIGQZxfgE_AQEBAQElAQFCFLZLpOiodwkajZMJLsjrkpr0HRMBSgNuYTJSAFoAYABorfyxJ3AAeAA"
    deals = fetch_closed_deals(access_token, limit=20)
    for d in deals:
        print(d)