import requests


def fetch_closed_deals(access_token, limit=10):
    """
    Fetch closed deals (closedwon / closedlost) with customer details from HubSpot.
    Requires a valid OAuth access token.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    deals_url = "https://api.hubapi.com/crm/v3/objects/deals"
    params = {
        "properties": "dealname,dealstage,amount,closedate",
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

        # Filter only closed deals
        if deal_stage in ["closedwon", "closedlost"]:
            deal_info = {
                "deal_id": deal.get("id"),
                "deal_name": deal_props.get("dealname"),
                "stage": deal_stage,
                "amount": deal_props.get("amount"),
                "closedate": deal_props.get("closedate"),
                "contacts": []
            }

            # Get associated contacts for this deal
            associations_url = f"https://api.hubapi.com/crm/v3/objects/deals/{deal.get('id')}/associations/contacts"
            assoc_resp = requests.get(associations_url, headers=headers)

            if assoc_resp.status_code == 200:
                assoc_data = assoc_resp.json().get("results", [])
                for assoc in assoc_data:
                    contact_id = assoc.get("id")

                    # Fetch contact details
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

            closed_deals.append(deal_info)

    return closed_deals


# Example usage
if __name__ == "__main__":
    access_token = "YOUR_OAUTH_ACCESS_TOKEN"
    deals = fetch_closed_deals(access_token)
    for d in deals:
        print(d)
