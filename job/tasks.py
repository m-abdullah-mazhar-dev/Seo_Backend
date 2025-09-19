# crm/tasks.py
import random
import re
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
from django.core.mail import EmailMultiAlternatives
# Render HTML content
from django.template.loader import render_to_string
from django.utils.html import strip_tags
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
    
    if not hasattr(connection, 'processed_deals'):
        return True

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
    
    # 🔥 NEW: Extract client name from email for sub-domain
    client_name = email.split('@')[0]  # Get part before @
    client_name = client_name.lower()   # Convert to lowercase
    client_name = re.sub(r'[^a-z0-9]', '', client_name)  # Remove special chars
    
    # Agar client_name empty hai to random ID use karo
    if not client_name:
        client_name = f"client{random.randint(1000, 9999)}"
    
    print(f"Client sub-domain name: {client_name}")

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
            'last_activity_time': deal.get('Last_Activity_Time', ''),
            'client_subdomain': client_name  # 
        }
    )
    
    # Generate feedback URLs
    # base_url = settings.FRONTEND_URL.rstrip('/')
    # yes_url = f"{base_url}/job/feedback/{feedback.token}/yes/"
    # no_url = f"{base_url}/job/feedback/{feedback.token}/no/"
    base_url = f"https://{client_name}.seo.galaxywholesales.com".rstrip('/')
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
        'current_date': timezone.now().isoformat(),
        'client_subdomain': client_name  # 🔥 Send to n8n
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
    


def should_skip_due_to_rate_limit(connection):
    """Check if we should skip this connection due to recent rate limiting"""
    # Safe access to metadata field
    if not hasattr(connection, 'metadata'):
        return False
    
    rate_limit_info = connection.metadata.get('rate_limit', {})
    retry_after = rate_limit_info.get('retry_after')
    
    if retry_after:
        try:
            retry_time = timezone.datetime.fromisoformat(retry_after)
            if timezone.now() < retry_time:
                return True
        except (ValueError, TypeError):
            pass
    
    return False

def handle_rate_limit(connection):
    """Handle rate limit by setting a retry time"""
    # Safe access to metadata field
    if not hasattr(connection, 'metadata'):
        return
    
    retry_after = timezone.now() + timezone.timedelta(hours=1)
    
    metadata = connection.metadata or {}
    metadata['rate_limit'] = {
        'retry_after': retry_after.isoformat(),
        'last_rate_limit': timezone.now().isoformat()
    }
    
    connection.metadata = metadata
    connection.save(update_fields=['metadata'])
    print(f"Rate limit encountered. Will retry after {retry_after}")






# crm/tasks.py
@shared_task
def check_jobber_closed_jobs():
    """Celery task to check Jobber CRM for closed jobs and send emails"""
    logger.info(f"🔄 Jobber closed jobs check started.")
    
    jobber_connections = CRMConnection.objects.filter(
        crm_type__provider='jobber',
        is_connected=True
    )
    
    results = []
    
    for connection in jobber_connections:
        result = process_jobber_connection(connection)
        results.append({
            'connection_id': connection.id,
            'connection_name': connection.connection_name,
            'result': result
        })
    
    return results

@shared_task(bind=True, max_retries=3)
def check_hubspot_closed_jobs(self):
    """Celery task to check HubSpot for closed jobs and send emails directly"""
    logger.info(f"🔄 HubSpot closed jobs check started.")
    
    hubspot_connections = CRMConnection.objects.filter(
        crm_type__provider='hubspot',
        is_connected=True
    )
    
    results = []
    
    for connection in hubspot_connections:
        if should_skip_due_to_rate_limit(connection):
            print(f"Skipping {connection.connection_name} due to recent rate limit")
            continue
            
        result = process_hubspot_connection(connection)
        results.append({
            'connection_id': connection.id,
            'connection_name': connection.connection_name,
            'result': result
        })
        
        if result.get('error') == 'RATE_LIMIT_EXCEEDED':
            handle_rate_limit(connection)
            self.retry(countdown=3600, max_retries=3)
    
    return results

@shared_task(bind=True, max_retries=3)
def check_salesforce_closed_jobs(self):
    """Celery task to check Salesforce for closed jobs and send emails directly"""
    logger.info(f"🔄 Salesforce closed jobs check started.")
    
    salesforce_connections = CRMConnection.objects.filter(
        crm_type__provider='salesforce',
        is_connected=True
    )
    
    results = []
    
    for connection in salesforce_connections:
        if should_skip_due_to_rate_limit(connection):
            print(f"Skipping {connection.connection_name} due to recent rate limit")
            continue
            
        result = process_salesforce_connection(connection)
        results.append({
            'connection_id': connection.id,
            'connection_name': connection.connection_name,
            'result': result
        })
        
        if result.get('error') == 'RATE_LIMIT_EXCEEDED':
            handle_rate_limit(connection)
            self.retry(countdown=3600, max_retries=3)
    
    return results

# tasks.py
def process_hubspot_connection(connection):
    """Process a single HubSpot connection for closed deals with token handling"""
    crm_service = get_crm_service(connection)
    
    # Check if connection is valid
    if not connection.is_connected:
        print(f"Skipping {connection.connection_name}: Connection not active")
        return {"success": False, "error": "CONNECTION_DISCONNECTED", "processed_count": 0}
    
    # Get last check time
    last_check = connection.last_sync or timezone.now() - timezone.timedelta(hours=24)
    
    # Fetch closed deals
    result = crm_service.get_closed_deals(last_check)
    
    if not result['success']:
        error = result.get('error', 'Unknown error')
        
        if error == 'TOKEN_EXPIRED':
            # Mark connection as disconnected
            connection.is_connected = False
            connection.save()
            return {"success": False, "error": "TOKEN_EXPIRED", "processed_count": 0}
        elif error == 'RATE_LIMIT_EXCEEDED':
            return {"success": False, "error": "RATE_LIMIT_EXCEEDED"}
        else:
            return {"success": False, "error": error, "processed_count": 0}
    
    closed_deals = result['data']
    processed_count = 0
    
    for deal in closed_deals:
        deal_id = deal.get('id')
        last_modified = deal.get('last_modified')
        
        if should_process_deal(deal_id, last_modified, connection):
            success = process_hubspot_deal(deal, connection)
            if success:
                processed_count += 1
    
    # Update last sync time if we processed any deals
    if processed_count > 0:
        connection.last_sync = timezone.now()
        connection.save(update_fields=['last_sync'])
    
    return {"success": True, "processed_count": processed_count, "total_count": len(closed_deals)}

def process_hubspot_deal(deal, connection):
    """Process a single HubSpot deal and send email directly"""
    deal_id = deal.get('id')
    
    # Extract email using HubSpot service
    crm_service = get_crm_service(connection)
    email = crm_service.extract_email_from_deal(deal)
    
    if not email or not crm_service.is_valid_email(email):
        print(f"Skipping deal {deal_id}: No valid email found")
        return False
    
    client_name = email.split('@')[0]
    client_name = client_name.lower()
    client_name = re.sub(r'[^a-z0-9]', '', client_name)
    
    if not client_name:
        client_name = f"client{random.randint(1000, 9999)}"
    
    # Get contact name
    contact_name = ""
    contacts = deal.get('contacts', [])
    if contacts:
        first_contact = contacts[0]
        first_name = first_contact.get('first_name', '')
        last_name = first_contact.get('last_name', '')
        contact_name = f"{first_name} {last_name}".strip()
    
    # Create feedback record
    feedback = ClientFeedback.objects.create(
        email=email,
        service_area=deal.get('deal_type', ''),
        job_id=deal_id,
        user=connection.user,
        crm_connection=connection,
        metadata={
            'deal_name': deal.get('name', 'Unknown Deal'),
            'amount': deal.get('amount', ''),
            'close_date': deal.get('close_date', ''),
            'contact_name': contact_name,
            'description': deal.get('description', ''),
            'contacts': deal.get('contacts', []),
            'client_subdomain': client_name  # 🔥 NEW


        }
    )
    
    # # Generate feedback URLs
    # base_url = settings.FRONTEND_URL.rstrip('/')
    # yes_url = f"{base_url}/job/feedback/{feedback.token}/yes/"
    # no_url = f"{base_url}/job/feedback/{feedback.token}/no/"

        # 🔥 UPDATED: Generate feedback URLs with client-specific sub-domain
    base_url = f"https://{client_name}.{settings.FRONTEND_URL}".rstrip('/')
    yes_url = f"{base_url}/job/feedback/{feedback.token}/yes/"
    no_url = f"{base_url}/job/feedback/{feedback.token}/no/"
    
    # Prepare context for email template
    context = {
        'yes_url': yes_url,
        'no_url': no_url,
        'job_id': deal_id,
        'deal_name': deal.get('name', 'Unknown Deal'),
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'to_email': email,
        'contact_name': contact_name,
        'current_date': timezone.now(),
    }
    
    # Send email directly using Django's email system
    return send_feedback_email(context)

def process_jobber_connection(connection):
    """Process a single Jobber connection for closed jobs"""
    crm_service = get_crm_service(connection)
    
    # Check if connection is valid
    if not connection.is_connected:
        print(f"Skipping {connection.connection_name}: Connection not active")
        return {"success": False, "error": "CONNECTION_DISCONNECTED", "processed_count": 0}
    
    # Get last check time
    last_check = connection.last_sync or timezone.now() - timezone.timedelta(hours=24)
    
    # Fetch closed jobs from Jobber
    result = crm_service.get_closed_jobs(last_check)
    
    if not result['success']:
        error = result.get('error', 'Unknown error')
        
        if 'expired' in error.lower() or 'invalid' in error.lower():
            # Mark connection as disconnected
            connection.is_connected = False
            connection.save()
            return {"success": False, "error": "TOKEN_EXPIRED", "processed_count": 0}
        else:
            return {"success": False, "error": error, "processed_count": 0}
    
    closed_jobs = result['data']
    processed_count = 0
    
    for job in closed_jobs:
        job_id = job.get('id')
        last_modified = job.get('updated_at')
        
        if should_process_deal(job_id, last_modified, connection):
            success = process_jobber_job(job, connection)
            if success:
                processed_count += 1
    
    # Update last sync time if we processed any jobs
    if processed_count > 0:
        connection.last_sync = timezone.now()
        connection.save(update_fields=['last_sync'])
    
    return {"success": True, "processed_count": processed_count, "total_count": len(closed_jobs)}

def process_jobber_job(job, connection):
    """Process a single Jobber job and send email"""
    job_id = job.get('id')
    
    # Extract email from job (assuming job has contact info)
    email = job.get('contact', {}).get('email', '')
    
    if not email or '@' not in email:
        print(f"Skipping job {job_id}: No valid email found")
        return False
    # 🔥 NEW: Extract client name from email for sub-domain
    client_name = email.split('@')[0]
    client_name = client_name.lower()
    client_name = re.sub(r'[^a-z0-9]', '', client_name)
    
    if not client_name:
        client_name = f"client{random.randint(1000, 9999)}"
    # Get contact name
    contact = job.get('contact', {})
    contact_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    
    # Create feedback record
    feedback = ClientFeedback.objects.create(
        email=email,
        service_area=job.get('service_type', ''),
        job_id=job_id,
        user=connection.user,
        crm_connection=connection,
        metadata={
            'job_title': job.get('title', 'Unknown Job'),
            'price': job.get('price', ''),
            'start_date': job.get('start_date', ''),
            'contact_name': contact_name,
            'description': job.get('description', ''),
            'status': job.get('status', ''),
            'client_subdomain': client_name  # 🔥 NEW
        }
    )
    
    # Generate feedback URLs
    base_url = f"https://{client_name}.{settings.FRONTEND_URL}".rstrip('/')
    yes_url = f"{base_url}/job/feedback/{feedback.token}/yes/"
    no_url = f"{base_url}/job/feedback/{feedback.token}/no/"


    
    # Prepare context for email template
    context = {
        'yes_url': yes_url,
        'no_url': no_url,
        'job_id': job_id,
        'deal_name': job.get('title', 'Unknown Job'),
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'to_email': email,
        'contact_name': contact_name,
        'current_date': timezone.now(),
    }
    
    # Send email directly using Django's email system
    return send_feedback_email(context)

def process_salesforce_connection(connection):
    """Process a single Salesforce connection for closed deals with token handling"""
    crm_service = get_crm_service(connection)
    
    # Check if connection is valid
    if not connection.is_connected:
        print(f"Skipping {connection.connection_name}: Connection not active")
        return {"success": False, "error": "CONNECTION_DISCONNECTED", "processed_count": 0}
    
    # Get last check time
    last_check = connection.last_sync or timezone.now() - timezone.timedelta(hours=24)
    
    # Fetch closed deals
    result = crm_service.get_closed_deals(last_check)
    
    if not result['success']:
        error = result.get('error', 'Unknown error')
        
        if error == 'TOKEN_EXPIRED':
            # Mark connection as disconnected
            connection.is_connected = False
            connection.save()
            return {"success": False, "error": "TOKEN_EXPIRED", "processed_count": 0}
        elif error == 'RATE_LIMIT_EXCEEDED':
            return {"success": False, "error": "RATE_LIMIT_EXCEEDED"}
        else:
            return {"success": False, "error": error, "processed_count": 0}
    
    closed_deals = result['data']
    processed_count = 0
    
    for deal in closed_deals:
        deal_id = deal.get('id')
        last_modified = deal.get('last_modified')
        
        if should_process_deal(deal_id, last_modified, connection):
            success = process_salesforce_deal(deal, connection)
            if success:
                processed_count += 1
    
    # Update last sync time if we processed any deals
    if processed_count > 0:
        connection.last_sync = timezone.now()
        connection.save(update_fields=['last_sync'])
    
    return {"success": True, "processed_count": processed_count, "total_count": len(closed_deals)}

def process_salesforce_deal(deal, connection):
    """Process a single Salesforce deal and send email directly"""
    deal_id = deal.get('id')
    
    # Extract email using Salesforce service
    crm_service = get_crm_service(connection)
    email = crm_service.extract_email_from_deal(deal)
    
    if not email or not crm_service.is_valid_email(email):
        print(f"Skipping deal {deal_id}: No valid email found")
        return False
    
    client_name = email.split('@')[0]
    client_name = client_name.lower()
    client_name = re.sub(r'[^a-z0-9]', '', client_name)
    
    if not client_name:
        client_name = f"client{random.randint(1000, 9999)}"
    
    # Get contact name
    contact_name = ""
    contact = deal.get('contact', {})
    if contact:
        contact_name = f"{contact.get('Name', '')}".strip()
    
    # Create feedback record
    feedback = ClientFeedback.objects.create(
        email=email,
        service_area=deal.get('stage', ''),
        job_id=deal_id,
        user=connection.user,
        crm_connection=connection,
        metadata={
            'deal_name': deal.get('name', 'Unknown Deal'),
            'amount': deal.get('amount', ''),
            'close_date': deal.get('close_date', ''),
            'contact_name': contact_name,
            'description': deal.get('description', ''),
            'stage': deal.get('stage', ''),
            'client_subdomain': client_name  # 🔥 NEW
        }
    )
    
    # Generate feedback URLs
    base_url = f"https://{client_name}.{settings.FRONTEND_URL}".rstrip('/')
    yes_url = f"{base_url}/job/feedback/{feedback.token}/yes/"
    no_url = f"{base_url}/job/feedback/{feedback.token}/no/"
    
    # Prepare context for email template
    context = {
        'yes_url': yes_url,
        'no_url': no_url,
        'job_id': deal_id,
        'deal_name': deal.get('name', 'Unknown Deal'),
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'to_email': email,
        'contact_name': contact_name,
        'current_date': timezone.now(),
    }
    
    # Send email directly using Django's email system
    return send_feedback_email(context)

def send_feedback_email(context):
    """Send feedback email using Django's email system"""
    try:
        # Render HTML content from template
        html_content = render_to_string('emails/client_feedback.html', context)
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create the email
        subject = f"Feedback Request for Your {context['deal_name']} Project"
        
        email_msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [context['to_email']]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()
        
        print(f"Successfully sent email to {context['to_email']}")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False