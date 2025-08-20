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

def get_crm_service(connection):
    """Factory function to get the appropriate CRM service"""
    if connection.crm_type.provider == 'hubspot':
        return HubSpotService(connection)
    elif connection.crm_type.provider == 'pipedrive':
        return PipedriveService(connection)
    else:
        raise ValueError(f"Unsupported CRM provider: {connection.crm_type.provider}")