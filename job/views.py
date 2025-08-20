from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from job.models import *
from job.utility import generate_structured_job_html, upload_job_post_to_wordpress
from seo_services.models import WordPressConnection
from .serializers import JobOnboardingFormSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from .models import ClientFeedback
from django.core.mail import send_mail
from django.conf import settings
from seo_services.models import OnboardingForm , BusinessLocation
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone


class CreateJobOnboardingFormAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = JobOnboardingFormSerializer(data=request.data)
        if serializer.is_valid():
            job_form = serializer.save()

            job_page = JobPage.objects.filter(user=request.user).last()
            if not job_page:
                return Response({"error": "No job page submitted for this user."}, status=400)
            
            try:
                html_content = generate_structured_job_html(job_form)
                upload_job_post_to_wordpress(job_form, job_page, html_content)
            except Exception as e:
                return Response({"error": f"Failed to publish job: {str(e)}"}, status=500)

            return Response({
                "message": "Onboarding form created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "message": "Form submission failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, pk=None, format=None):
        if pk:
            form = get_object_or_404(JobOnboardingForm, pk=pk)
            serializer = JobOnboardingFormSerializer(form)
            return Response({
                "message": f"Onboarding form ID {pk} fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            forms = JobOnboardingForm.objects.all()
            serializer = JobOnboardingFormSerializer(forms, many=True)
            return Response({
                "message": "All onboarding forms fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
    def patch(self, request, pk, format=None):
        try:
            instance = JobOnboardingForm.objects.get(pk=pk)
        except JobOnboardingForm.DoesNotExist:
            return Response({
                "message": f"Onboarding form with ID {pk} does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = JobOnboardingFormSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": f"Onboarding form ID {pk} updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Update failed due to invalid data.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    

class SubmitJobPageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        page_url = request.data.get("page_url")

        if not page_url:
            return Response({"error": "Page URL is required."}, status=400)

        try:
            wp_conn = user.wordpress_connection
        except WordPressConnection.DoesNotExist:
            return Response({"error": "User has not connected WordPress."}, status=400)

        job_page = JobPage.objects.create(
            user=user,
            wordpress_connection=wp_conn,
            page_url=page_url
        )

        return Response({"message": "Job page submitted successfully."})
    

class JobClosedAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        service_area = request.data.get("service_area")
        job_id = request.data.get("job_id")

        print("Job Closed from n8n:", email, service_area, job_id)
        feedback = ClientFeedback.objects.create(
            email=email,
            service_area=service_area,
            job_id=job_id
        )

        yes_url = f"{settings.FRONTEND_RESET_URL}job/feedback/{feedback.token}/yes/"
        no_url = f"{settings.FRONTEND_RESET_URL}job/feedback/{feedback.token}/no/"

        # Send email
        # send_mail(
        #     subject="Are you satisfied with the service?",
        #     message=f"Please let us know:\nYes: {yes_url}\nNo: {no_url}",
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[email],
        # )

        # Prepare context for the email template
        context = {
            'yes_url': yes_url,
            'no_url': no_url,
            'job_id': job_id,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'to_email': email,
            'current_date': timezone.now(),
        }

        # Render HTML content
        html_content = render_to_string('emails/client_feedback.html', context)
        
        # Create the email
        subject = "Your Feedback Means A Lot"
        text_content = strip_tags(html_content)  # Fallback text version
        
        email_msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()

        return Response({"status": "email sent"})


# class FeedbackAPI(APIView):
#     def get(self, request, token, answer):
#         try:
#             feedback = ClientFeedback.objects.get(token=token)
#         except ClientFeedback.DoesNotExist:
#             return Response({"error": "Invalid or expired link"}, status=404)

#         # Update feedback
#         feedback.is_satisfied = (answer == "yes")
#         feedback.save()

#         # Base response
#         response_data = {
#             "satisfied": feedback.is_satisfied,
#             "email": feedback.email,
#             "job_id": feedback.job_id,
#             "service_area": feedback.service_area,
#         }

#         if feedback.is_satisfied:
#             # Now find business location using service_area + user
#             onboarding_form = OnboardingForm.objects.filter(email=feedback.email).first()
#             if onboarding_form:
#                 location = BusinessLocation.objects.filter(onboarding_form=onboarding_form).first()
#                 if location:
#                     response_data["review_url"] = location.location_url
#         else:
#             response_data["feedback_url"] = "https://your-feedback-form.com"

#         return Response(response_data, status=200)




# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import requests
import json
import uuid

from .models import CRMType, CRMConnection, ClientFeedback
from .serializers import (
    CRMTypeSerializer, CRMConnectionSerializer, 
    OAuthInitSerializer, OAuthCallbackSerializer, ClientFeedbackSerializer
)
from .crm_services import get_crm_service
from django.conf import settings

class CRMTypeListAPIView(APIView):
    """Get list of supported CRM types"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        crm_types = CRMType.objects.filter(is_active=True)
        serializer = CRMTypeSerializer(crm_types, many=True)
        return Response(serializer.data)

class CRMConnectionListAPIView(APIView):
    """List user's CRM connections"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        connections = CRMConnection.objects.filter(user=request.user)
        serializer = CRMConnectionSerializer(connections, many=True)
        return Response(serializer.data)

class CRMConnectionCreateAPIView(APIView):
    """Create a new CRM connection"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CRMConnectionSerializer(data=request.data)
        if serializer.is_valid():
            crm_type = serializer.validated_data['crm_type']
            api_key = serializer.validated_data.get('api_key')
            api_domain = serializer.validated_data.get('api_domain')
            
            # Create connection but don't save yet
            connection = CRMConnection(
                user=request.user,
                crm_type=crm_type,
                connection_name=serializer.validated_data.get('connection_name', f"{crm_type.name} Connection"),
                api_key=api_key,
                api_domain=api_domain
            )
            
            # Verify the connection
            crm_service = get_crm_service(connection)
            is_valid = crm_service.verify_connection()
            
            if is_valid:
                connection.is_connected = True
                connection.save()
                return Response(CRMConnectionSerializer(connection).data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": "Invalid credentials or unable to connect to CRM"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OAuthInitAPIView(APIView):
    """Initialize OAuth flow for a CRM"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = OAuthInitSerializer(data=request.data)
        if serializer.is_valid():
            crm_type = get_object_or_404(CRMType, id=serializer.validated_data['crm_type_id'])
            redirect_uri = serializer.validated_data['redirect_uri'] # just neede to be picked from setting
            
            if crm_type.auth_type not in ['oauth', 'both']:
                return Response(
                    {"error": "This CRM does not support OAuth authentication"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate state parameter for security
            state = str(uuid.uuid4())
            request.session['oauth_state'] = state
            request.session['oauth_crm_type'] = crm_type.id
            request.session['oauth_redirect_uri'] = redirect_uri
            
            # Build the authorization URL
            auth_url = self.build_authorization_url(crm_type, redirect_uri, state)
            
            return Response({"authorization_url": auth_url})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def build_authorization_url(self, crm_type, redirect_uri, state):
        if crm_type.provider == 'hubspot':
            params = {
                'client_id': settings.HUBSPOT_CLIENT_ID,
                'redirect_uri': redirect_uri,
                'scope': 'crm.objects.deals.read crm.objects.deals.write',
                'state': state,
            }
            
            from urllib.parse import urlencode
            return f"https://app.hubspot.com/oauth/authorize?{urlencode(params)}"
        
        # Add other CRM providers here
        return None

class OAuthCallbackAPIView(APIView):
    """Handle OAuth callback from CRM"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = OAuthCallbackSerializer(data=request.GET)
        if serializer.is_valid():
            code = serializer.validated_data['code']
            state = serializer.validated_data['state']
            
            # Verify state parameter
            if state != request.session.get('oauth_state'):
                return Response(
                    {"error": "Invalid state parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            crm_type_id = request.session.get('oauth_crm_type')
            redirect_uri = request.session.get('oauth_redirect_uri')
            
            if not all([crm_type_id, redirect_uri]):
                return Response(
                    {"error": "OAuth session data missing"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            crm_type = get_object_or_404(CRMType, id=crm_type_id)
            
            # Exchange code for access token
            token_data = self.exchange_code_for_token(crm_type, code, redirect_uri)
            
            if token_data:
                # Create or update CRM connection
                connection, created = CRMConnection.objects.get_or_create(
                    user=request.user,
                    crm_type=crm_type,
                    defaults={
                        'connection_name': f"{crm_type.name} Connection",
                        'oauth_access_token': token_data['access_token'],
                        'oauth_refresh_token': token_data.get('refresh_token'),
                        'oauth_token_expiry': timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
                        'is_connected': True
                    }
                )
                
                if not created:
                    connection.oauth_access_token = token_data['access_token']
                    connection.oauth_refresh_token = token_data.get('refresh_token')
                    connection.oauth_token_expiry = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                    connection.is_connected = True
                    connection.save()
                
                # Clear session data
                for key in ['oauth_state', 'oauth_crm_type', 'oauth_redirect_uri']:
                    if key in request.session:
                        del request.session[key]
                
                return Response(
                    {"message": "CRM connected successfully", "connection_id": connection.id}
                )
            else:
                return Response(
                    {"error": "Failed to obtain access token"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def exchange_code_for_token(self, crm_type, code, redirect_uri):
        if crm_type.provider == 'hubspot':
            url = "https://api.hubapi.com/oauth/v1/token"
            
            data = {
                'grant_type': 'authorization_code',
                'client_id': settings.HUBSPOT_CLIENT_ID,
                'client_secret': settings.HUBSPOT_CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'code': code
            }
            
            try:
                response = requests.post(url, data=data)
                if response.status_code == 200:
                    return response.json()
            except requests.RequestException:
                pass
        
        return None

class CRMConnectionDetailAPIView(APIView):
    """Get, update, or delete a specific CRM connection"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(CRMConnection, id=pk, user=user)
    
    def get(self, request, pk):
        connection = self.get_object(pk, request.user)
        serializer = CRMConnectionSerializer(connection)
        return Response(serializer.data)
    
    def put(self, request, pk):
        connection = self.get_object(pk, request.user)
        serializer = CRMConnectionSerializer(connection, data=request.data, partial=True)
        
        if serializer.is_valid():
            # If API key is being updated, verify it
            if 'api_key' in serializer.validated_data:
                connection.api_key = serializer.validated_data['api_key']
                
                # Verify the connection
                crm_service = get_crm_service(connection)
                is_valid = crm_service.verify_connection()
                
                if not is_valid:
                    return Response(
                        {"error": "Invalid API key"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        connection = self.get_object(pk, request.user)
        connection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CRMWebhookAPIView(APIView):
    """Handle incoming webhooks from n8n with CRM job data"""
    permission_classes = [AllowAny]
    
    def post(self, request, secret_token):
        try:
            crm_connection = CRMConnection.objects.get(webhook_secret_token=secret_token)
        except CRMConnection.DoesNotExist:
            return Response({"error": "Invalid webhook token"}, status=status.HTTP_404_NOT_FOUND)
        
        email = request.data.get("email")
        service_area = request.data.get("service_area")
        job_id = request.data.get("job_id")
        
        if not all([email, service_area, job_id]):
            return Response(
                {"error": "Missing required fields: email, service_area, or job_id"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create feedback record
        feedback = ClientFeedback.objects.create(
            email=email,
            service_area=service_area,
            job_id=job_id,
            user=crm_connection.user,
            crm_connection=crm_connection
        )
        
        # Generate feedback URLs
        yes_url = f"{settings.FRONTEND_URL}job/feedback/{feedback.token}/yes/"
        no_url = f"{settings.FRONTEND_URL}job/feedback/{feedback.token}/no/"
        
        # Prepare context for the email template
        context = {
            'yes_url': yes_url,
            'no_url': no_url,
            'job_id': job_id,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'to_email': email,
            'current_date': timezone.now(),
        }
        
        # Render HTML content
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.core.mail import EmailMultiAlternatives
        
        html_content = render_to_string('emails/client_feedback.html', context)
        
        # Create the email
        subject = "Your Feedback Means A Lot"
        text_content = strip_tags(html_content)
        
        email_msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()
        
        return Response({"status": "email sent"})

class FeedbackAPI(APIView):
    """Handle feedback responses"""
    permission_classes = [AllowAny]
    
    def get(self, request, token, answer):
        try:
            feedback = ClientFeedback.objects.get(token=token)
        except ClientFeedback.DoesNotExist:
            return Response({"error": "Invalid or expired link"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update feedback
        feedback.is_satisfied = (answer == "yes")
        feedback.save()
        
        # Base response
        response_data = {
            "satisfied": feedback.is_satisfied,
            "email": feedback.email,
            "job_id": feedback.job_id,
            "service_area": feedback.service_area,
        }
        
        if feedback.is_satisfied:
            # Now find business location using service_area + user
            # from .models import OnboardingForm, BusinessLocation
            
            onboarding_form = OnboardingForm.objects.filter(email=feedback.email).first()
            if onboarding_form:
                location = BusinessLocation.objects.filter(onboarding_form=onboarding_form).first()
                if location:
                    response_data["review_url"] = location.location_url
        else:
            response_data["feedback_url"] = "https://your-feedback-form.com"
        
        return Response(response_data, status=status.HTTP_200_OK)

class CRMJobCreateAPIView(APIView):
    """Create a job in the connected CRM"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crm_service = get_crm_service(connection)
        result = crm_service.create_job(request.data)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

class CRMJobCloseAPIView(APIView):
    """Close a job in the connected CRM"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id, job_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        won = request.data.get('won', True)
        crm_service = get_crm_service(connection)
        result = crm_service.close_job(job_id, won)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)