# crm_services.py
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json

class CRMServiceBase:
    """Base class for CRM services"""
    
    def __init__(self, connection):
        self.connection = connection
        self.crm_type = connection.crm_type
    
    def verify_connection(self):
        """Verify if the connection is valid"""
        raise NotImplementedError("Subclasses must implement verify_connection")
    
    def create_job(self, job_data):
        """Create a job in the CRM"""
        raise NotImplementedError("Subclasses must implement create_job")
    
    def close_job(self, job_id):
        """Close a job in the CRM"""
        raise NotImplementedError("Subclasses must implement close_job")

class HubSpotService(CRMServiceBase):
    """HubSpot CRM service implementation"""

    def __init__(self, connection):
        super().__init__(connection)
        self.api_base = "https://api.hubapi.com"
    
    def get_api_base_url(self):
        return self.api_base
    
    def verify_connection(self):
        """Verify HubSpot connection using OAuth token"""
        url = "https://api.hubapi.com/oauth/v1/access-tokens/%s" % self.connection.oauth_access_token
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
            return False
        except requests.RequestException:
            return False
    def refresh_token(self):
        """Refresh HubSpot OAuth token"""
        if not self.connection.oauth_refresh_token:
            return False
        
        token_url = "https://api.hubapi.com/oauth/v1/token"
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': settings.HUBSPOT_CLIENT_ID,
            'client_secret': settings.HUBSPOT_CLIENT_SECRET,
            'refresh_token': self.connection.oauth_refresh_token
        }
        
        try:
            response = requests.post(token_url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.connection.oauth_access_token = token_data['access_token']
                self.connection.oauth_refresh_token = token_data.get('refresh_token', self.connection.oauth_refresh_token)
                self.connection.oauth_token_expiry = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                self.connection.save()
                return True
        except requests.RequestException:
            pass
        
        return False
    
    def ensure_valid_token(self):
        """Ensure we have a valid access token"""
        if self.connection.is_token_expired():
            success = self.refresh_token()
            if not success:
                # If refresh fails, mark as disconnected
                self.connection.is_connected = False
                self.connection.save()
                return False
        return True
    def get_closed_deals(self, last_check_time=None):
        """Fetch closed deals from HubSpot with proper token handling"""
        if not self.ensure_valid_token():
            return {"success": False, "error": "Invalid or expired token"}
        
        headers = {
            "Authorization": f"Bearer {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        # Build properties array
        properties = ["dealname", "dealstage", "amount", "closedate", "dealtype", "description", "hs_lastmodifieddate"]
        
        # Build filter for closed deals
        filter_groups = [{
            "filters": [{
                "propertyName": "dealstage",
                "operator": "IN",
                "values": ["closedwon", "closedlost"]
            }]
        }]
        
        # Add time filter if provided
        if last_check_time:
            last_check_ms = int(last_check_time.timestamp() * 1000)
            filter_groups[0]["filters"].append({
                "propertyName": "hs_lastmodifieddate",
                "operator": "GTE",
                "value": last_check_ms
            })
        
        url = f"{self.api_base}/crm/v3/objects/deals/search"
        
        # CORRECTED payload structure - use propertyName instead of property
        payload = {
            "properties": properties,
            "filterGroups": filter_groups,
            "sorts": [{
                "propertyName": "hs_lastmodifieddate",  # FIXED: propertyName instead of property
                "direction": "ASCENDING"
            }],
            "limit": 100
        }
        
        print(f"HubSpot API request: {json.dumps(payload, indent=2)}")  # Debug
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                deals = data.get("results", [])
                print(f"Found {len(deals)} closed deals in HubSpot")
                
                # Enrich deals with contact emails
                enriched_deals = []
                for deal in deals:
                    enriched_deal = self.enrich_deal_with_contacts(deal, headers)
                    enriched_deals.append(enriched_deal)
                
                return {"success": True, "data": enriched_deals}
            
            elif response.status_code == 401:  # Token expired
                print("HubSpot token expired. Attempting refresh...")
                if self.refresh_token():
                    # Retry with new token
                    return self.get_closed_deals(last_check_time)
                else:
                    self.connection.is_connected = False
                    self.connection.save()
                    return {"success": False, "error": "TOKEN_EXPIRED"}
            
            elif response.status_code == 429:  # Rate limit
                return {"success": False, "error": "RATE_LIMIT_EXCEEDED"}
            
            else:
                error_msg = f"HubSpot Error {response.status_code}: {response.text}"
                print(f"HubSpot API error: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}

    def enrich_deal_with_contacts(self, deal, headers):
        """Enrich deal with contact information including emails"""
        deal_id = deal.get("id")
        properties = deal.get("properties", {})
        
        enriched_deal = {
            "id": deal_id,
            "name": properties.get("dealname"),
            "stage": properties.get("dealstage"),
            "amount": properties.get("amount"),
            "close_date": properties.get("closedate"),
            "deal_type": properties.get("dealtype"),
            "description": properties.get("description"),
            "last_modified": properties.get("hs_lastmodifieddate"),
            "contacts": [],
            "emails": []
        }
        
        # Get associated contacts using the associations endpoint
        deal_url = f"{self.api_base}/crm/v3/objects/deals/{deal_id}"
        params = {
            "properties": "dealname,dealstage",
            "associations": "contacts"
        }
        
        try:
            response = requests.get(deal_url, headers=headers, params=params)
            if response.status_code == 200:
                deal_data = response.json()
                associations = deal_data.get("associations", {})
                
                # Get contact associations
                contact_associations = associations.get("contacts", {}).get("results", [])
                
                for assoc in contact_associations:
                    contact_id = assoc.get("id")
                    if contact_id:
                        contact_data = self.get_contact_details(contact_id, headers)
                        if contact_data:
                            enriched_deal["contacts"].append(contact_data)
                            
                            # Collect emails for easy access
                            email = contact_data.get("email")
                            if email and "@" in email:
                                enriched_deal["emails"].append(email)
        
        except requests.RequestException:
            pass
        
        return enriched_deal
    
    def get_contact_details(self, contact_id, headers):
        """Get detailed contact information"""
        url = f"{self.api_base}/crm/v3/objects/contacts/{contact_id}"
        
        params = {
            "properties": "firstname,lastname,email,phone,company,lifecyclestage",
            "archived": "false"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                contact_data = response.json()
                properties = contact_data.get("properties", {})
                
                return {
                    "id": contact_id,
                    "first_name": properties.get("firstname"),
                    "last_name": properties.get("lastname"),
                    "email": properties.get("email"),
                    "phone": properties.get("phone"),
                    "company": properties.get("company"),
                    "lifecycle_stage": properties.get("lifecyclestage")
                }
        except requests.RequestException:
            pass
        
        return None
    
    def extract_email_from_deal(self, deal):
        """Extract email from HubSpot deal data"""
        emails = deal.get("emails", [])
        if emails:
            return emails[0]  # Return first email found
        
        # Fallback: check contacts
        contacts = deal.get("contacts", [])
        for contact in contacts:
            email = contact.get("email")
            if email and "@" in email:
                return email
        
        return ""
    
    def is_valid_email(self, email):
        """Check if email is valid"""
        if not email or "@" not in email:
            return False
        
        # Filter out common placeholder emails
        invalid_domains = ['noemail.invalid', 'example.com', 'test.com', 'placeholder.com']
        for domain in invalid_domains:
            if domain in email:
                return False
        
        return True
    
    def create_job(self, job_data):
        """Create a deal in HubSpot"""
        url = "https://api.hubapi.com/crm/v3/objects/deals"
        
        headers = {
            "Authorization": f"Bearer {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        properties = {
            "dealname": job_data.get("job_name", "New Job"),
            "dealstage": "appointmentscheduled",  # Initial stage
            "pipeline": "default",
            "amount": job_data.get("amount", ""),
            "closedate": job_data.get("close_date", ""),
        }
        
        data = {
            "properties": properties
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 201:
                result = response.json()
                return {"success": True, "job_id": result.get("id"), "data": result}
            return {"success": False, "error": response.text}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def close_job(self, job_id, won=True):
        """Close a deal in HubSpot (mark as won or lost)"""
        url = f"https://api.hubapi.com/crm/v3/objects/deals/{job_id}"
        
        headers = {
            "Authorization": f"Bearer {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        # Determine the stage based on won/lost
        stage = "closedwon" if won else "closedlost"
        
        data = {
            "properties": {
                "dealstage": stage
            }
        }
        
        try:
            response = requests.patch(url, headers=headers, json=data)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {"success": False, "error": response.text}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

class PipedriveService(CRMServiceBase):
    """Pipedrive CRM service implementation"""
    
    def verify_connection(self):
        """Verify Pipedrive connection using API key"""
        url = f"{self.connection.api_domain}/api/v1/users/me"
        
        params = {
            "api_token": self.connection.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return True
            return False
        except requests.RequestException:
            return False
    
    def create_job(self, job_data):
        """Create a deal in Pipedrive"""
        url = f"{self.connection.api_domain}/api/v1/deals"
        
        params = {
            "api_token": self.connection.api_key
        }
        
        data = {
            "title": job_data.get("job_name", "New Job"),
            "stage_id": 1,  # Initial stage
            "status": "open",
            "value": job_data.get("amount", 0),
            "currency": job_data.get("currency", "USD"),
        }
        
        try:
            response = requests.post(url, params=params, json=data)
            if response.status_code == 201:
                result = response.json()
                return {"success": True, "job_id": result.get("data", {}).get("id"), "data": result}
            return {"success": False, "error": response.text}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def close_job(self, job_id, won=True):
        """Close a deal in Pipedrive (mark as won or lost)"""
        url = f"{self.connection.api_domain}/api/v1/deals/{job_id}"
        
        params = {
            "api_token": self.connection.api_key
        }
        
        # Determine the status based on won/lost
        status = "won" if won else "lost"
        
        data = {
            "status": status
        }
        
        try:
            response = requests.put(url, params=params, json=data)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {"success": False, "error": response.text}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

# class JobberService(CRMServiceBase):
#     """Jobber CRM service implementation"""
    
#     def __init__(self, connection):
#         super().__init__(connection)
#         self.api_base = "https://api.getjobber.com"
    
#     def get_api_base_url(self):
#         return self.api_base
    
#     def verify_connection(self):
#         """Verify Jobber connection using OAuth token"""
#         url = f"{self.api_base}/api/v1/users/me"
        
#         headers = {
#             "Authorization": f"Bearer {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         try:
#             response = requests.get(url, headers=headers)
#             if response.status_code == 200:
#                 return True
            
#             # If token is expired, try to refresh it
#             if response.status_code == 401:
#                 return self.refresh_token()
                
#             return False
#         except requests.RequestException as e:
#             print(f"Jobber connection verification error: {str(e)}")
#             return False
    
#     def refresh_token(self):
#         """Refresh Jobber access token using refresh token"""
#         if not self.connection.oauth_refresh_token:
#             return False
        
#         token_url = f"{self.api_base}/oauth/token"
        
#         data = {
#             'grant_type': 'refresh_token',
#             'client_id': settings.JOBBER_CLIENT_ID,
#             'client_secret': settings.JOBBER_CLIENT_SECRET,
#             'refresh_token': self.connection.oauth_refresh_token
#         }
        
#         try:
#             response = requests.post(token_url, data=data)
#             if response.status_code == 200:
#                 token_data = response.json()
#                 self.connection.oauth_access_token = token_data['access_token']
#                 self.connection.oauth_refresh_token = token_data.get('refresh_token', self.connection.oauth_refresh_token)
#                 self.connection.oauth_token_expiry = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
#                 self.connection.save()
#                 return True
#             else:
#                 print(f"Jobber token refresh failed: {response.text}")
#                 return False
#         except requests.RequestException as e:
#             print(f"Jobber token refresh error: {str(e)}")
#             return False
    
#     def ensure_valid_token(self):
#         """Ensure we have a valid access token"""
#         if self.connection.is_token_expired():
#             success = self.refresh_token()
#             if not success:
#                 # If refresh fails, mark as disconnected
#                 self.connection.is_connected = False
#                 self.connection.save()
#                 return False
#         return True
    
#     def create_job(self, job_data):
#         """Create a job in Jobber CRM"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Invalid or expired token. Please re-authenticate with Jobber."}
        
#         url = f"{self.api_base}/api/v1/jobs"
        
#         headers = {
#             "Authorization": f"Bearer {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         # Map job data to Jobber job structure
#         jobber_job_data = {
#             "title": job_data.get("job_name", "New Job"),
#             "description": job_data.get("description", ""),
#             "status": "scheduled",  # Initial status
#             "start_date": job_data.get("start_date", ""),
#             "end_date": job_data.get("end_date", ""),
#             "estimated_duration": job_data.get("estimated_duration", ""),
#             "price": job_data.get("amount", ""),
#         }
        
#         # Remove empty fields
#         jobber_job_data = {k: v for k, v in jobber_job_data.items() if v is not None and v != ""}
        
#         try:
#             response = requests.post(url, headers=headers, json=jobber_job_data)
#             print(f"Jobber create job response: {response.status_code}")
#             print(f"Jobber create job response text: {response.text}")
            
#             if response.status_code == 201:
#                 result = response.json()
#                 job_id = result.get("id")
#                 return {"success": True, "job_id": job_id, "data": result}
#             else:
#                 error_msg = self.handle_jobber_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def close_job(self, job_id, won=True):
#         """Close a job in Jobber CRM (mark as completed or cancelled)"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Failed to refresh access token"}
        
#         url = f"{self.api_base}/api/v1/jobs/{job_id}"
        
#         headers = {
#             "Authorization": f"Bearer {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         # Determine the status based on won/lost
#         status = "completed" if won else "cancelled"
        
#         data = {
#             "status": status
#         }
        
#         try:
#             response = requests.patch(url, headers=headers, json=data)
#             print(f"Jobber close job response: {response.status_code}")
#             print(f"Jobber close job response text: {response.text}")
            
#             if response.status_code == 200:
#                 return {"success": True, "data": response.json()}
#             else:
#                 error_msg = self.handle_jobber_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def create_contact(self, contact_data):
#         """Create a contact in Jobber CRM"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Invalid or expired token"}
        
#         url = f"{self.api_base}/api/v1/contacts"
        
#         headers = {
#             "Authorization": f"Bearer {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         # Map contact data to Jobber contact structure
#         jobber_contact_data = {
#             "first_name": contact_data.get("first_name", ""),
#             "last_name": contact_data.get("last_name", ""),
#             "email": contact_data.get("email", ""),
#             "phone": contact_data.get("phone", ""),
#             "address": {
#                 "street": contact_data.get("street", ""),
#                 "city": contact_data.get("city", ""),
#                 "state": contact_data.get("state", ""),
#                 "postal_code": contact_data.get("postal_code", ""),
#                 "country": contact_data.get("country", "US")
#             },
#             "notes": contact_data.get("notes", "")
#         }
        
#         # Remove empty fields
#         jobber_contact_data = {k: v for k, v in jobber_contact_data.items() if v is not None and v != ""}
        
#         try:
#             response = requests.post(url, headers=headers, json=jobber_contact_data)
#             print(f"Jobber create contact response: {response.status_code}")
            
#             if response.status_code == 201:
#                 result = response.json()
#                 contact_id = result.get("id")
#                 return {"success": True, "contact_id": contact_id, "data": result}
#             else:
#                 error_msg = self.handle_jobber_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def update_contact(self, contact_id, contact_data):
#         """Update a contact in Jobber CRM"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Invalid or expired token"}
        
#         url = f"{self.api_base}/api/v1/contacts/{contact_id}"
        
#         headers = {
#             "Authorization": f"Bearer {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         # Map contact data to Jobber contact structure
#         jobber_contact_data = {
#             "first_name": contact_data.get("first_name", ""),
#             "last_name": contact_data.get("last_name", ""),
#             "email": contact_data.get("email", ""),
#             "phone": contact_data.get("phone", ""),
#             "address": {
#                 "street": contact_data.get("street", ""),
#                 "city": contact_data.get("city", ""),
#                 "state": contact_data.get("state", ""),
#                 "postal_code": contact_data.get("postal_code", ""),
#                 "country": contact_data.get("country", "US")
#             },
#             "notes": contact_data.get("notes", "")
#         }
        
#         # Remove empty fields
#         jobber_contact_data = {k: v for k, v in jobber_contact_data.items() if v is not None and v != ""}
        
#         try:
#             response = requests.patch(url, headers=headers, json=jobber_contact_data)
#             print(f"Jobber update contact response: {response.status_code}")
            
#             if response.status_code == 200:
#                 result = response.json()
#                 return {"success": True, "data": result}
#             else:
#                 error_msg = self.handle_jobber_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def list_contacts(self, limit=100, offset=0):
#         """List contacts from Jobber CRM"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Invalid or expired token"}
        
#         url = f"{self.api_base}/api/v1/contacts"
        
#         headers = {
#             "Authorization": f"Bearer {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         params = {
#             "limit": limit,
#             "offset": offset
#         }
        
#         try:
#             response = requests.get(url, headers=headers, params=params)
#             print(f"Jobber list contacts response: {response.status_code}")
            
#             if response.status_code == 200:
#                 result = response.json()
#                 contacts = result.get("contacts", [])
#                 return {"success": True, "contacts": contacts, "data": result}
#             else:
#                 error_msg = self.handle_jobber_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def get_closed_jobs(self, last_check_time=None):
#         """Fetch closed jobs from Jobber CRM"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Invalid or expired token"}
        
#         url = f"{self.api_base}/api/v1/jobs"
        
#         headers = {
#             "Authorization": f"Bearer {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         # Build query parameters for closed jobs
#         params = {
#             "status": "completed",  # Only get completed jobs
#             "limit": 100,
#             "include": "contact"  # Include contact information
#         }
        
#         # Add time filter if provided
#         if last_check_time:
#             params["updated_since"] = last_check_time.isoformat()
        
#         try:
#             response = requests.get(url, headers=headers, params=params)
#             print(f"Jobber get closed jobs response: {response.status_code}")
            
#             if response.status_code == 200:
#                 result = response.json()
#                 jobs = result.get("jobs", [])
#                 print(f"Found {len(jobs)} closed jobs")
#                 return {"success": True, "data": jobs}
#             else:
#                 error_msg = self.handle_jobber_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def handle_jobber_error(self, response):
#         """Handle Jobber API errors consistently"""
#         try:
#             error_data = response.json()
#             if 'errors' in error_data:
#                 errors = error_data['errors']
#                 if isinstance(errors, list) and len(errors) > 0:
#                     error_msg = errors[0].get('message', 'Unknown error')
#                     error_code = errors[0].get('code', 'UNKNOWN')
#                     return f"Jobber Error {error_code}: {error_msg}"
#                 else:
#                     return f"Jobber Error: {str(errors)}"
#             else:
#                 return f"Jobber Error: {response.text}"
#         except:
#             return f"Jobber Error: HTTP {response.status_code}"



class JobberService(CRMServiceBase):
    ENDPOINT = "https://api.getjobber.com/api/graphql"

    def _h(self):
        """Prepare headers for Jobber GraphQL requests"""
        headers = {
            "Authorization": f"Bearer {self.connection.oauth_access_token}",
            "Content-Type": "application/json",
        }
        if getattr(self.connection, "graphql_version", None):
            headers["X-JOBBER-GRAPHQL-VERSION"] = self.connection.graphql_version
        return headers

    def verify_connection(self):
        """Check if the Jobber connection is valid by querying account info"""
        query = {"query": "query { account { id name } }"}
        try:
            r = requests.post(self.ENDPOINT, headers=self._h(), json=query, timeout=30)
            return r.status_code == 200 and "data" in r.json()
        except requests.RequestException:
            return False
        
    def get_jobs(self):
        """Fetch jobs from Jobber with proper error handling"""
        query = """
        query GetJobs {
        jobs {
            nodes {
            id
            jobNumber
            title
            jobStatus
            billingType
            client {
                id
                firstName
                lastName
            }
            property {
                id
                address {
                street1
                city
                postalCode
                }
            }
            total
            createdAt
            updatedAt
            }
        }
        }
        """

        try:
            response = requests.post(
                self.ENDPOINT,
                headers=self._h(),
                json={"query": query},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                if "errors" in result:
                    return {"success": False, "error": result["errors"]}

                jobs = result.get("data", {}).get("jobs", {}).get("nodes", [])
                return {"success": True, "data": jobs}

            return {"success": False, "error": response.text}

        except requests.RequestException as e:
            return {"success": False, "error": str(e)}


def get_crm_service(connection):
    """Factory function to get the appropriate CRM service"""
    if connection.crm_type.provider == 'hubspot':
        return HubSpotService(connection)
    elif connection.crm_type.provider == 'pipedrive':
        return PipedriveService(connection)
    elif connection.crm_type.provider == 'zoho':
        return ZohoCRMService(connection)
    elif connection.crm_type.provider == 'jobber':
        return JobberService(connection)
    else:
        raise ValueError(f"Unsupported CRM provider: {connection.crm_type.provider}")
    
# class ZohoCRMService(CRMServiceBase):
#     """Zoho CRM service implementation"""
    
#     def __init__(self, connection):
#         super().__init__(connection)
#         self.api_domain = self.get_api_domain()
    
#     def get_api_domain(self):
#         """Extract API domain for Zoho - defaults to .com"""
#         return "com"  # Default to .com domain
    
#     def get_api_base_url(self):
#         """Get the correct API base URL for Zoho"""
#         return f"https://www.zohoapis.{self.api_domain}"
    
#     def verify_connection(self):
#         """Verify Zoho CRM connection using OAuth token"""
#         url = f"{self.get_api_base_url()}/crm/v2/org"
        
#         headers = {
#             "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         try:
#             response = requests.get(url, headers=headers)
#             if response.status_code == 200:
#                 return True
            
#             # If token is expired, try to refresh it
#             if response.status_code == 401:
#                 return self.refresh_token()
                
#             return False
#         except requests.RequestException as e:
#             print(f"Zoho connection verification error: {str(e)}")
#             return False
    
#     def refresh_token(self):
#         """Refresh Zoho access token using refresh token"""
#         if not self.connection.oauth_refresh_token:
#             return False
        
#         # Try different Zoho domains for token refresh
#         domains = ['com', 'eu', 'in', 'au']  # Common Zoho domains
        
#         for domain in domains:
#             url = f"https://accounts.zoho.{domain}/oauth/v2/token"
            
#             data = {
#                 'grant_type': 'refresh_token',
#                 'client_id': settings.ZOHO_CLIENT_ID,
#                 'client_secret': settings.ZOHO_CLIENT_SECRET,
#                 'refresh_token': self.connection.oauth_refresh_token
#             }
            
#             try:
#                 response = requests.post(url, data=data)
#                 if response.status_code == 200:
#                     token_data = response.json()
#                     self.connection.oauth_access_token = token_data['access_token']
#                     self.connection.oauth_token_expiry = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
#                     self.connection.save()
#                     return True
#             except requests.RequestException:
#                 continue
        
#         return False
    
#     def ensure_valid_token(self):
#         """Ensure we have a valid access token, refresh if needed"""
#         if self.connection.is_token_expired():
#             return self.refresh_token()
#         return True
    
#     def create_job(self, job_data):
#         """Create a deal in Zoho CRM"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Failed to refresh access token"}
        
#         url = f"{self.get_api_base_url()}/crm/v2/Deals"
        
#         headers = {
#             "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         # Format date for Zoho
#         close_date = job_data.get("close_date", "")
#         if close_date:
#             close_date = close_date.split('T')[0]  # Remove time portion if present
        
#         deal_data = {
#             "Deal_Name": job_data.get("job_name", "New Job"),
#             "Stage": "Qualification",  # Initial stage
#             "Amount": job_data.get("amount", ""),
#             "Closing_Date": close_date,
#         }
        
#         data = {
#             "data": [deal_data]
#         }
        
#         try:
#             response = requests.post(url, headers=headers, json=data)
#             if response.status_code == 201:
#                 result = response.json()
#                 deal_id = result['data'][0]['details']['id']
#                 return {"success": True, "job_id": deal_id, "data": result}
#             else:
#                 error_msg = self.handle_zoho_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def close_job(self, job_id, won=True):
#         """Close a deal in Zoho CRM (mark as won or lost)"""
#         if not self.ensure_valid_token():
#             return {"success": False, "error": "Failed to refresh access token"}
        
#         url = f"{self.get_api_base_url()}/crm/v2/Deals/{job_id}"
        
#         headers = {
#             "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
#             "Content-Type": "application/json"
#         }
        
#         # Determine the stage based on won/lost
#         stage = "Closed Won" if won else "Closed Lost"
        
#         data = {
#             "data": [{
#                 "Stage": stage
#             }]
#         }
        
#         try:
#             response = requests.put(url, headers=headers, json=data)
#             if response.status_code == 200:
#                 return {"success": True, "data": response.json()}
#             else:
#                 error_msg = self.handle_zoho_error(response)
#                 return {"success": False, "error": error_msg}
#         except requests.RequestException as e:
#             return {"success": False, "error": f"Request failed: {str(e)}"}
    
#     def handle_zoho_error(self, response):
#         """Handle Zoho API errors consistently"""
#         try:
#             error_data = response.json()
#             if 'data' in error_data and isinstance(error_data['data'], list):
#                 error_msg = error_data['data'][0].get('message', 'Unknown error')
#                 error_code = error_data['data'][0].get('code', 'UNKNOWN')
        #         return f"Zoho Error {error_code}: {error_msg}"
        #     else:
        #         return f"Zoho Error: {response.text}"
        # except:
        #     return f"Zoho Error: HTTP {response.status_code}"



class ZohoCRMService(CRMServiceBase):
    """Zoho CRM service implementation"""
    
    def __init__(self, connection):
        super().__init__(connection)
        self.api_domain = "com"  # From the successful response
    
    def get_api_base_url(self):
        """Get the correct API base URL for Zoho"""
        return "https://www.zohoapis.com"
    
    def verify_connection(self):
        """Verify Zoho CRM connection using OAuth token"""
        url = f"{self.get_api_base_url()}/crm/v2/org"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return True
            
            # If token is expired, try to refresh it
            if response.status_code == 401:
                return self.refresh_token()
                
            return False
        except requests.RequestException as e:
            print(f"Zoho connection verification error: {str(e)}")
            return False
    
    def refresh_token_with_scopes(self):
        """Refresh token and request additional scopes if needed"""
        if not self.connection.oauth_refresh_token:
            return False
        
        token_url = "https://accounts.zoho.com/oauth/v2/token"
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': settings.ZOHO_CLIENT_ID,
            'client_secret': settings.ZOHO_CLIENT_SECRET,
            'refresh_token': self.connection.oauth_refresh_token
        }
        
        try:
            response = requests.post(token_url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.connection.oauth_access_token = token_data['access_token']
                self.connection.oauth_token_expiry = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                self.connection.save()
                return True
            else:
                # If refresh fails due to scope issues, we need to re-authenticate
                print(f"Token refresh failed: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"Zoho token refresh error: {str(e)}")
            return False
    
    def ensure_valid_token(self):
        """Ensure we have a valid access token with proper scopes"""
        if self.connection.is_token_expired():
            success = self.refresh_token_with_scopes()
            if not success:
                # If refresh fails, the token might have insufficient scopes
                # We should mark the connection as needing re-authentication
                self.connection.is_connected = False
                self.connection.save()
                return False
        return True
    
    def create_job(self, job_data):
        """Create a deal in Zoho CRM"""
        if not self.ensure_valid_token():
            return {"success": False, "error": "Invalid or expired token. Please re-authenticate with Zoho."}
        
        # Check if connection is still valid
        if not self.connection.is_connected:
            return {"success": False, "error": "CRM connection needs re-authentication. Please reconnect Zoho CRM."}
        
        url = f"{self.get_api_base_url()}/crm/v2/Deals"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        # Format date for Zoho (YYYY-MM-DD)
        close_date = job_data.get("close_date", "")
        if close_date:
            if 'T' in close_date:
                close_date = close_date.split('T')[0]  # Remove time portion
        
        deal_data = {
            "Deal_Name": job_data.get("job_name", "New Job"),
            "Stage": "Qualification",  # Initial stage
            "Amount": job_data.get("amount", ""),
            "Closing_Date": close_date,
        }
        
        # Remove empty fields
        deal_data = {k: v for k, v in deal_data.items() if v is not None and v != ""}
        
        data = {
            "data": [deal_data]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            print(f"Zoho create deal response: {response.status_code}")
            print(f"Zoho create deal response text: {response.text}")
            
            if response.status_code == 201:
                result = response.json()
                deal_id = result['data'][0]['details']['id']
                return {"success": True, "job_id": deal_id, "data": result}
            else:
                # Handle scope mismatch specifically
                if response.status_code == 401 and "OAUTH_SCOPE_MISMATCH" in response.text:
                    self.connection.is_connected = False
                    self.connection.save()
                    return {"success": False, "error": "Insufficient permissions. Please re-authenticate with Zoho CRM."}
                
                error_msg = self.handle_zoho_error(response)
                return {"success": False, "error": error_msg}
        except requests.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
    
    def close_job(self, job_id, won=True):
        """Close a deal in Zoho CRM (mark as won or lost)"""
        if not self.ensure_valid_token():
            return {"success": False, "error": "Failed to refresh access token"}
        
        url = f"{self.get_api_base_url()}/crm/v2/Deals/{job_id}"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        # Determine the stage based on won/lost
        stage = "Closed Won" if won else "Closed Lost"
        
        data = {
            "data": [{
                "Stage": stage
            }]
        }
        
        try:
            response = requests.put(url, headers=headers, json=data)
            print(f"Zoho close deal response: {response.status_code}")
            print(f"Zoho close deal response text: {response.text}")
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_msg = self.handle_zoho_error(response)
                return {"success": False, "error": error_msg}
        except requests.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
    
    def handle_zoho_error(self, response):
        """Handle Zoho API errors consistently"""
        try:
            error_data = response.json()
            if 'data' in error_data and isinstance(error_data['data'], list):
                error_msg = error_data['data'][0].get('message', 'Unknown error')
                error_code = error_data['data'][0].get('code', 'UNKNOWN')
                return f"Zoho Error {error_code}: {error_msg}"
            else:
                return f"Zoho Error: {response.text}"
        except:
            return f"Zoho Error: HTTP {response.status_code}"
    
    # def get_closed_deals(self, last_check_time=None):
    #     """Fetch closed deals from Zoho CRM with proper filtering and debugging"""
    #     if not self.ensure_valid_token():
    #         return {"success": False, "error": "Invalid or expired token"}
        
    #     url = f"{self.get_api_base_url()}/crm/v2/Deals"
        
    #     headers = {
    #         "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
    #         "Content-Type": "application/json"
    #     }
        
    #     # Build query criteria for closed won deals
    #     criteria = "(Stage:equals:Closed Won)"
        
    #     # Add time filter if provided
    #     if last_check_time:
    #         last_check_str = last_check_time.strftime("%Y-%m-%dT%H:%M:%S%z")
    #         if len(last_check_str) == 25 and last_check_str[-2] == '0':
    #             last_check_str = last_check_str[:-2] + ':' + last_check_str[-2:]
    #         criteria = f"({criteria} and Last_Activity_Time:greater_than:{last_check_str})"
        
    #     params = {
    #         "criteria": criteria,
    #         "fields": "id,Deal_Name,Amount,Closing_Date,Contact_Name,Description,Service_Area,Last_Activity_Time",
    #         "sort_by": "Last_Activity_Time",
    #         "sort_order": "asc",
    #         "per_page": 200
    #     }
        
    #     try:
    #         response = requests.get(url, headers=headers, params=params)
    #         print(f"Zoho get closed deals response: {response.status_code}")
            
    #         if response.status_code == 200:
    #             data = response.json()
    #             deals = data.get('data', [])
    #             print(f"Found {len(deals)} closed deals")
                
    #             # DEBUG: Print detailed information about each deal
    #             for i, deal in enumerate(deals):
    #                 print(f"\n=== Deal {i+1} ===")
    #                 print(f"ID: {deal.get('id')}")
    #                 print(f"Name: {deal.get('Deal_Name')}")
    #                 print(f"Stage: {deal.get('Stage')}")
    #                 print(f"Contact_Name: {deal.get('Contact_Name')}")
    #                 print(f"Contact_Name type: {type(deal.get('Contact_Name'))}")
                    
    #                 # Debug contact information in detail
    #                 contact_info = deal.get('Contact_Name')
    #                 if contact_info:
    #                     if isinstance(contact_info, dict):
    #                         print(f"Contact ID: {contact_info.get('id')}")
    #                         print(f"Contact Name: {contact_info.get('name')}")
                            
    #                         # Try to fetch contact details if we have an ID
    #                         if contact_info.get('id'):
    #                             self.debug_contact_details(contact_info['id'], headers)
    #                     else:
    #                         print(f"Contact info is not a dictionary: {contact_info}")
                    
    #                 print("All deal fields:", list(deal.keys()))
                
    #             return {"success": True, "data": deals}
    #         else:
    #             error_msg = self.handle_zoho_error(response)
    #             return {"success": False, "error": error_msg}
    #     except requests.RequestException as e:
    #         return {"success": False, "error": f"Request failed: {str(e)}"}

    # services.py
    def get_closed_deals(self, last_check_time=None):
        """Fetch closed deals from Zoho CRM with time filtering"""
        if not self.ensure_valid_token():
            return {"success": False, "error": "Invalid or expired token"}
        
        url = f"{self.get_api_base_url()}/crm/v2/Deals"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        # Build query criteria for closed won deals
        criteria = "(Stage:equals:Closed Won)"
        
        # Add time filter if provided - ONLY get deals modified since last check
        if last_check_time:
            # Convert to Zoho format
            last_check_str = last_check_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            # Format timezone offset properly
            if len(last_check_str) == 25 and last_check_str[-2] == '0':
                last_check_str = last_check_str[:-2] + ':' + last_check_str[-2:]
            
            # Use Modified_Time instead of Last_Activity_Time for better accuracy
            criteria = f"({criteria} and Modified_Time:greater_than:{last_check_str})"
            print(f"Filtering deals modified after: {last_check_str}")
        
        params = {
            "criteria": criteria,
            "fields": "id,Deal_Name,Amount,Closing_Date,Contact_Name,Description,Service_Area,Last_Activity_Time,Modified_Time",
            "sort_by": "Modified_Time",  # Sort by modification time
            "sort_order": "asc",  # Get oldest first
            "per_page": 200
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"Zoho get closed deals response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                deals = data.get('data', [])
                print(f"Found {len(deals)} closed deals since last check")
                return {"success": True, "data": deals}
            else:
                error_msg = self.handle_zoho_error(response)
                return {"success": False, "error": error_msg}
        except requests.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        
    def debug_contact_details(self, contact_id, headers):
        """Fetch and debug contact details"""
        try:
            contact_url = f"{self.get_api_base_url()}/crm/v2/Contacts/{contact_id}"
            response = requests.get(contact_url, headers=headers)
            
            if response.status_code == 200:
                contact_data = response.json()
                contact = contact_data.get('data', [{}])[0]
                print(f"=== Contact Details for ID {contact_id} ===")
                print(f"Email: {contact.get('Email')}")
                print(f"First Name: {contact.get('First_Name')}")
                print(f"Last Name: {contact.get('Last_Name')}")
                print(f"Full Name: {contact.get('Full_Name')}")
                print("All contact fields:", list(contact.keys()))
            else:
                print(f"Failed to fetch contact {contact_id}: {response.status_code}")
        except Exception as e:
            print(f"Error fetching contact details: {str(e)}")
    
    def extract_email_from_deal(self, deal):
        """Extract email from deal data with detailed debugging"""
        print(f"\n=== Extracting email from deal {deal.get('id')} ===")
        
        # Check Contact_Name field first
        contact_info = deal.get('Contact_Name')
        print(f"Contact_Name field: {contact_info}")
        
        if contact_info and isinstance(contact_info, dict):
            contact_id = contact_info.get('id')
            if contact_id:
                print(f"Found contact ID: {contact_id}")
                # Fetch contact email
                email = self.get_contact_email(contact_id)
                if email and self.is_valid_email(email):  # Add validation check
                    print(f"Found valid email from contact: {email}")
                    return email
                else:
                    print(f"Invalid email found: {email}")
        
        print("No valid email found")
        return ''

    def is_valid_email(self, email):
        """Check if email is valid (not a placeholder)"""
        if not email or '@' not in email:
            return False
        
        # Filter out common placeholder emails
        invalid_domains = ['noemail.invalid', 'example.com', 'test.com', 'placeholder.com']
        for domain in invalid_domains:
            if domain in email:
                return False
        
        return True
    
    def get_contact_email(self, contact_id):
        """Get email from contact by ID"""
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            contact_url = f"{self.get_api_base_url()}/crm/v2/Contacts/{contact_id}"
            response = requests.get(contact_url, headers=headers)
            
            if response.status_code == 200:
                contact_data = response.json()
                contact = contact_data.get('data', [{}])[0]
                return contact.get('Email', '')
        except Exception as e:
            print(f"Error fetching contact email: {str(e)}")
        
        return ''