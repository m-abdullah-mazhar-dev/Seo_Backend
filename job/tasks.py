# crm/tasks.py
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from SEO_Automation.db_router import set_current_service
from job.models import CRMConnection, ClientFeedback
from job.crm_services import get_crm_service
import requests
import json
from datetime import datetime
import uuid

import logging

logger = logging.getLogger(__name__)

@shared_task
def check_zoho_closed_jobs():
    
    """Celery task to check Zoho CRM for closed jobs and send to n8n"""
    # Get all active Zoho connections
    logger.info(f"🔄SEO tasks started.")
    set_current_service("seo")
    zoho_connections = CRMConnection.objects.filter(
        crm_type__provider='zoho',
        is_connected=True
    )
    
    results = []
    
    for connection in zoho_connections:
        result = process_zoho_connection(connection)
        results.append({
            'connection_id': connection.id,
            'connection_name': connection.connection_name,
            'result': result
        })
    
    return results

# def process_zoho_connection(connection):
#     """Process a single Zoho connection for closed deals"""
#     crm_service = get_crm_service(connection)
    
#     # Get last check time from connection metadata or use default (last 24 hours)
#     last_check = connection.last_sync or timezone.now() - timezone.timedelta(hours=24)
    
#     # Fetch closed deals since last check
#     result = crm_service.get_closed_deals(last_check)
    
#     if not result['success']:
#         return {"success": False, "error": result['error'], "processed_count": 0}
    
#     closed_deals = result['data']
#     processed_count = 0
    
#     for deal in closed_deals:
#         success = process_closed_deal(deal, connection)
#         if success:
#             processed_count += 1
    
#     # Update last sync time if we processed any deals
#     if processed_count > 0:
#         connection.last_sync = timezone.now()
#         connection.save(update_fields=['last_sync'])
    
#     return {"success": True, "processed_count": processed_count, "total_count": len(closed_deals)}


def process_zoho_connection(connection):
    """Process a single Zoho connection for closed deals with duplicate prevention"""
    crm_service = get_crm_service(connection)
    
    # Get last check time from connection metadata
    last_check = connection.last_sync or timezone.now() - timezone.timedelta(hours=24)
    
    # Fetch closed deals since last check ONLY
    result = crm_service.get_closed_deals(last_check)
    
    if not result['success']:
        return {"success": False, "error": result['error'], "processed_count": 0}
    
    closed_deals = result['data']
    processed_count = 0
    newly_processed_deals = []
    
    for deal in closed_deals:
        deal_id = deal.get('id')
        last_activity_time = deal.get('Last_Activity_Time')
        
        # Check if this deal was already processed (using last activity time)
        if should_process_deal(deal_id, last_activity_time, connection):
            success = process_closed_deal(deal, connection)
            if success:
                processed_count += 1
                newly_processed_deals.append({
                    'deal_id': deal_id,
                    'last_activity_time': last_activity_time,
                    'processed_at': timezone.now().isoformat()
                })
    
    # Update last sync time and processed deals
    if processed_count > 0:
        connection.last_sync = timezone.now()
        
        # Add newly processed deals to the tracking list
        current_processed = connection.processed_deals or []
        current_processed.extend(newly_processed_deals)
        
        # Keep only the last 1000 processed deals to avoid bloating
        if len(current_processed) > 1000:
            current_processed = current_processed[-1000:]
        
        connection.processed_deals = current_processed
        connection.save(update_fields=['last_sync', 'processed_deals'])
    
    return {"success": True, "processed_count": processed_count, "total_count": len(closed_deals)}

def should_process_deal(deal_id, last_activity_time, connection):
    """Check if a deal should be processed (avoid duplicates)"""
    if not deal_id:
        return False
    
    # If no last activity time, process it
    if not last_activity_time:
        return True
    
    # Check if this deal was already processed
    processed_deals = connection.processed_deals or []
    
    for processed_deal in processed_deals:
        if (processed_deal.get('deal_id') == deal_id and 
            processed_deal.get('last_activity_time') == last_activity_time):
            print(f"Skipping deal {deal_id}: Already processed")
            return False
    
    return True

# crm/tasks.py
# crm/tasks.py
def process_closed_deal(deal, connection):
    """Process a single closed deal, create feedback record, and send to n8n"""
    # Extract deal data
    deal_id = deal.get('id')
    print(f"\n=== Processing deal {deal_id} ===")
    
    # Get CRM service and extract email with debugging
    crm_service = get_crm_service(connection)
    email = crm_service.extract_email_from_deal(deal)
    
    print(f"Extracted email: {email}")
    
    if not email or '@' not in email:
        print(f"Skipping deal {deal_id}: No valid email found")
        return False
    
    # Get contact name from deal
    contact_name = ''
    contact_info = deal.get('Contact_Name', {})
    if isinstance(contact_info, dict):
        contact_name = contact_info.get('name', '')
    
    print(f"Creating feedback record for email: {email}")
    
    # Create feedback record - FIXED: use correct field names
    feedback = ClientFeedback.objects.create(
        email=email,
        job_id=deal_id,
        service_area=deal.get('Service_Area', ''),
        user=connection.user,
        crm_connection=connection,
        metadata={  # This should work now after adding the field
            'deal_name': deal.get('Deal_Name', 'Unknown Deal'),
            'amount': deal.get('Amount', ''),
            'close_date': deal.get('Closing_Date', ''),
            'contact_name': contact_name,
            'description': deal.get('Description', ''),
            'last_activity_time': deal.get('Last_Activity_Time', '')
        }
    )
    
    # Generate feedback URLs
    base_url = settings.FRONTEND_URL.rstrip('/')
    yes_url = f"{base_url}/job/feedback/{feedback.token}/yes/"
    no_url = f"{base_url}/job/feedback/{feedback.token}/no/"
    
    print(f"Generated feedback URLs - Yes: {yes_url}, No: {no_url}")
    
    # Prepare data for n8n
    deal_data = {
        'id': deal_id,
        'name': deal.get('Deal_Name', 'Unknown Deal'),
        'amount': deal.get('Amount', ''),
        'close_date': deal.get('Closing_Date', ''),
        'contact_name': contact_name,
        'email': email,
        'service_area': deal.get('Service_Area', ''),
        'description': deal.get('Description', ''),
        'last_activity_time': deal.get('Last_Activity_Time', ''),
        'user_id': connection.user.id,
        'connection_id': connection.id,
        'feedback_token': str(feedback.token),
        'yes_url': yes_url,
        'no_url': no_url,
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'current_date': timezone.now().isoformat()
    }
    
    # Send to n8n webhook
    return send_to_n8n(deal_data)

def send_to_n8n(deal_data):
    """Send deal data to n8n's webhook for email sending"""
    # This should be your n8n webhook URL
    n8n_webhook_url = "https://abd-dev.app.n8n.cloud/webhook-test/webhook/zoho-closed-deals"
    
    payload = {
        'email': deal_data['email'],
        'job_id': deal_data['id'],
        'service_area': deal_data['service_area'],
        'deal_name': deal_data['name'],
        'amount': deal_data['amount'],
        'close_date': deal_data['close_date'],
        'contact_name': deal_data['contact_name'],
        'description': deal_data['description'],
        'last_activity_time': deal_data['last_activity_time'],
        'user_id': deal_data['user_id'],
        'connection_id': deal_data['connection_id'],
        'feedback_token': deal_data['feedback_token'],
        'yes_url': deal_data['yes_url'],
        'no_url': deal_data['no_url'],
        'from_email': deal_data['from_email'],
        'current_date': deal_data['current_date']
    }
    
    try:
        response = requests.post(n8n_webhook_url, json=payload, timeout=30)
        if response.status_code in [200, 201, 202]:
            print(f"Successfully sent deal {deal_data['id']} to n8n")
            return True
        else:
            print(f"Failed to send to n8n: {response.status_code} - {response.text}")
            return False
    except requests.RequestException as e:
        print(f"Error sending to n8n: {str(e)}")
        return False