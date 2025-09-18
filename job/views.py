from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from g_matrix.google_service import build_service
from g_matrix.models import GoogleAnalyticsToken, SearchConsoleToken
from job.models import *
from job.utility import convert_template_to_html, create_initial_job_blog_task, generate_structured_job_html, map_cost_structure, process_job_template_html, sync_job_keywords, upload_job_post_to_wordpress
from seo_services.models import BusinessDetails, WordPressConnection
from seo_services.upload_blog_to_wp import upload_blog_to_wordpress
from .serializers import FeedbackFormResponseSerializer, JobBlogSerializer, JobOnboardingFormSerializer, JobTaskSerializer
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
import logging
from bs4 import BeautifulSoup
from rest_framework.views import APIView
import re
logger = logging.getLogger(__name__)




class SubmitJobPageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        page_url = request.data.get("page_url")

        if not page_url:
            return Response({"error": "Page URL is required."}, status=400)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404


    

#
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import JobOnboardingForm, JobPage
from .serializers import JobOnboardingFormSerializer
# from .tasks import run_job_template_generation, create_initial_job_tasks
# from .wordpress import generate_structured_job_html, upload_job_post_to_wordpress


# class CreateJobOnboardingFormAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, format=None):
#         user = request.user

#         # Prevent duplicate forms (uncomment if needed)
#         # if JobOnboardingForm.objects.filter(user=user).exists():
#         #     return Response({
#         #         "message": "Job onboarding form already exists for this user."
#         #     }, status=status.HTTP_200_OK)

#         serializer = JobOnboardingFormSerializer(data=request.data)
#         if serializer.is_valid():
#             job_form = serializer.save(user=user)

#             print("✅ Job form saved:", job_form)
        

#             # WordPress publishing (optional)
#             # job_page = JobPage.objects.filter(user=request.user).last()
#             # if not job_page:
#             #     return Response({"error": "No job page submitted for this user."}, status=400)
#             # try:
#             #     html_content = generate_structured_job_html(job_form)
#             #     upload_job_post_to_wordpress(job_form, job_page, html_content)
#             # except Exception as e:
#             #     return Response({"error": f"Failed to publish job: {str(e)}"}, status=500)

#             # Background Task Creation
#             run_job_template_generation(job_form)
#             try:
#                 create_initial_job_tasks(user, job_form)
#                 print("Task created successfully")
#             except Exception as e:
#                 return Response({"error": f"Failed to Create Job blog: {str(e)}"}, status=500)

#             return Response({
#                 "message": "Onboarding form created successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_201_CREATED)

#         return Response({
#             "message": "Form submission failed",
#             "errors": serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)

#     def get(self, request, pk=None, format=None):
#         if pk:
#             form = get_object_or_404(JobOnboardingForm, pk=pk, user=request.user)
#             serializer = JobOnboardingFormSerializer(form)
#             return Response({
#                 "message": f"Onboarding form ID {pk} fetched successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_200_OK)
#         else:
#             forms = JobOnboardingForm.objects.filter(user=request.user)
#             serializer = JobOnboardingFormSerializer(forms, many=True)
#             return Response({
#                 "message": "All onboarding forms fetched successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_200_OK)



#     def patch(self, request, pk, format=None):
#         try:
#             instance = JobOnboardingForm.objects.get(pk=pk, user=request.user)
#         except JobOnboardingForm.DoesNotExist:
#             return Response({
#                 "message": f"Onboarding form with ID {pk} does not exist."
#             }, status=status.HTTP_404_NOT_FOUND)

#         serializer = JobOnboardingFormSerializer(instance, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
            
#             # Trigger WordPress update after successful form update
#             try:
#                 # Find the latest job template for this form
#                 job_template = JobTemplate.objects.filter(
#                     job_onboarding=instance
#                 ).order_by('-created_at').first()
                
#                 if job_template:
#                     # Regenerate and update the WordPress post
#                     updated_template = run_job_template_generation(instance, is_update=True)
                    
#                     if updated_template and updated_template.status == 'completed':
#                         return Response({
#                             "message": f"Onboarding form ID {pk} updated successfully and WordPress post refreshed.",
#                             "data": serializer.data
#                         }, status=status.HTTP_200_OK)
#                     else:
#                         return Response({
#                             "message": f"Form updated but WordPress sync failed or is still processing.",
#                             "data": serializer.data
#                         }, status=status.HTTP_200_OK)
#                 else:
#                     # If no template exists, create a new one
#                     run_job_template_generation(instance, is_update=False)
#                     return Response({
#                         "message": f"Onboarding form ID {pk} updated successfully. Creating new WordPress post.",
#                         "data": serializer.data
#                     }, status=status.HTTP_200_OK)
                    
#             except Exception as e:
#                 # Log the error but don't fail the request
#                 logger.error(f"WordPress update failed: {str(e)}")
#                 return Response({
#                     "message": f"Form updated but WordPress sync failed: {str(e)}",
#                     "data": serializer.data
#                 }, status=status.HTTP_200_OK)
        
#         return Response({
#             "message": "Update failed due to invalid data.",
#             "errors": serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)
            
            

            

#     def delete(self, request, pk, format=None):
#         try:
#             form = JobOnboardingForm.objects.get(pk=pk, user=request.user)
#         except JobOnboardingForm.DoesNotExist:
#             return Response({
#                 "message": f"Onboarding form with ID {pk} does not exist."
#             }, status=status.HTTP_404_NOT_FOUND)

#         form.delete()
#         return Response({
#             "message": f"Onboarding form ID {pk} deleted successfully."
#         }, status=status.HTTP_204_NO_CONTENT)




from rest_framework.pagination import PageNumberPagination
import math
from .models import JobOnboardingForm, JobTemplate
from .serializers import JobOnboardingFormSerializer

class JobOnboardingPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.count = queryset.count()
        self.page_size = self.get_page_size(request) or self.page_size

        try:
            return super().paginate_queryset(queryset, request, view=view)
        except Exception:
            # If page is invalid, don't break — return empty list
            self.page = None
            return []

    def get_paginated_response(self, data):
        total_items = self.count
        page_size = self.page_size
        total_pages = math.ceil(total_items / page_size) if page_size else 1
        current_page = (
            self.page.number if self.page else int(self.request.query_params.get("page", 1))
        )

        return Response({
            "success": True,
            "message": "Job onboarding forms retrieved successfully.",
            "pagination": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": current_page,
                "page_size": page_size,
            },
            "data": data if data is not None else [],
        })

class CreateJobOnboardingFormAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = JobOnboardingPagination

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    def post(self, request, format=None):
        user = request.user

        # Prevent duplicate forms (uncomment if needed)
        # if JobOnboardingForm.objects.filter(user=user).exists():
        #     return Response({
        #         "message": "Job onboarding form already exists for this user."
        #     }, status=status.HTTP_200_OK)

        serializer = JobOnboardingFormSerializer(data=request.data)
        if serializer.is_valid():
            job_form = serializer.save(user=user)

            print("✅ Job form saved:", job_form)
        

            # WordPress publishing (optional)
            # job_page = JobPage.objects.filter(user=request.user).last()
            # if not job_page:
            #     return Response({"error": "No job page submitted for this user."}, status=400)
            # try:
            #     html_content = generate_structured_job_html(job_form)
            #     upload_job_post_to_wordpress(job_form, job_page, html_content)
            # except Exception as e:
            #     return Response({"error": f"Failed to publish job: {str(e)}"}, status=500)

            # Background Task Creation
            run_job_template_generation(job_form)
            try:
                create_initial_job_tasks(user, job_form)
                print("Task created successfully")
            except Exception as e:
                return Response({"error": f"Failed to Create Job blog: {str(e)}"}, status=500)

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
            form = get_object_or_404(JobOnboardingForm, pk=pk, user=request.user)
            serializer = JobOnboardingFormSerializer(form)
            return Response({
                "message": f"Onboarding form ID {pk} fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            forms = JobOnboardingForm.objects.filter(user=request.user)
            
            # Add pagination for the list view
            page = self.paginate_queryset(forms)
            if page is not None:
                serializer = JobOnboardingFormSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            # Fallback if pagination is disabled
            serializer = JobOnboardingFormSerializer(forms, many=True)
            return Response({
                "message": "All onboarding forms fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

    def patch(self, request, pk, format=None):
        try:
            instance = JobOnboardingForm.objects.get(pk=pk, user=request.user)
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


    def delete(self, request, pk, format=None):
        try:
            form = JobOnboardingForm.objects.get(pk=pk, user=request.user)
        except JobOnboardingForm.DoesNotExist:
            return Response({
                "message": f"Onboarding form with ID {pk} does not exist."
            }, status=status.HTTP_404_NOT_FOUND)


        job_templates = JobTemplate.objects.filter(job_onboarding=form)
        

        for job_template in job_templates:
            if job_template.wp_page_id and hasattr(request.user, 'wordpress_connection'):
                from .utility import delete_wordpress_post
                delete_wordpress_post(request.user.wordpress_connection, job_template.wp_page_id)
        
        form.delete()
        
        return Response({
            "message": f"Onboarding form ID {pk} deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)



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
            # redirect_uri = serializer.validated_data['redirect_uri'] # just neede to be picked from setting
            redirect_uri = settings.HUBSPOT_REDIRECT_URI # just neede to be picked from setting
            print(redirect_uri)
            
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

            request.session.save()

            print(state)

                        # Also store in database as backup
            OAuthState.objects.create(
                user=request.user,
                state=state,
                crm_type_id=crm_type.id,
                redirect_uri=redirect_uri
            )
            
            # Build the authorization URL
            auth_url = self.build_authorization_url(crm_type, redirect_uri, state)
            
            return Response({"authorization_url": auth_url})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def build_authorization_url(self, crm_type, redirect_uri, state):
        if crm_type.provider == 'hubspot':
            params = {
                'client_id': settings.HUBSPOT_CLIENT_ID,
                'redirect_uri': redirect_uri,
                'scope': 'crm.objects.deals.read crm.objects.deals.write crm.objects.contacts.read',
                'state': state,
            }
            
            from urllib.parse import urlencode
            return f"https://app.hubspot.com/oauth/authorize?{urlencode(params)}"
        
        elif crm_type.provider == 'zoho':

            # Correct Zoho CRM scopes - space separated, not comma separated
            scopes = [
                'ZohoCRM.modules.ALL',
                'ZohoCRM.settings.ALL',
                'aaaserver.profile.READ'
            ]
            scope_string = ' '.join(scopes)
            params = {
                'client_id': settings.ZOHO_CLIENT_ID,
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'scope': scope_string,
                'state': state,
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            from urllib.parse import urlencode
            return f"https://accounts.zoho.com/oauth/v2/auth?{urlencode(params)}"
        
        elif crm_type.provider == 'jobber':
            from urllib.parse import urlencode
            # Jobber OAuth 2.0 authorization URL
            params = {
                "client_id": settings.JOBBER_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "graphql_api",
                "state": state,
            }
            return f"https://api.getjobber.com/api/oauth/authorize?{urlencode(params)}"
        
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
            location = request.GET.get('location', '')  
            
            # Verify state parameter
            if state != request.session.get('oauth_state'):
                try:
                    oauth_state = OAuthState.objects.get(state=state, user=request.user)
                    if not oauth_state.is_expired():
                        # Use database values as backup
                        crm_type_id = oauth_state.crm_type_id
                        redirect_uri = oauth_state.redirect_uri
                        # Clean up the used state
                        oauth_state.delete()
                    else:
                        return Response(
                            {"error": "Expired state parameter"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except OAuthState.DoesNotExist:
                    return Response(
                        {"error": "Invalid state parameter"},
                        status=status.HTTP_400_BAD_REQUEST)
            else:
                crm_type_id = request.session.get('oauth_crm_type')
                redirect_uri = request.session.get('oauth_redirect_uri')

                            # Clear session data
                for key in ['oauth_state', 'oauth_crm_type', 'oauth_redirect_uri']:
                    if key in request.session:
                        del request.session[key]
                
            if not all([crm_type_id, redirect_uri]):
                return Response(
                    {"error": "OAuth session data missing"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            crm_type = get_object_or_404(CRMType, id=crm_type_id)
            
            # Exchange code for access token
            token_data = self.exchange_code_for_token(crm_type, code, redirect_uri,location)
            
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
    
    def exchange_code_for_token(self, crm_type, code, redirect_uri,location=''):
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
        elif crm_type.provider == 'zoho':
            # Use .com domain (most common)
            token_url = "https://accounts.zoho.com/oauth/v2/token"
            
            data = {
                'grant_type': 'authorization_code',
                'client_id': settings.ZOHO_CLIENT_ID,
                'client_secret': settings.ZOHO_CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'code': code
            }
            
            try:
                response = requests.post(token_url, data=data)
                print(f"Zoho token exchange response: {response.status_code}")
                print(f"Zoho token exchange response text: {response.text}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    # Log the detailed error
                    print(f"Zoho token exchange failed: {response.text}")
                    
            except requests.RequestException as e:
                print(f"Zoho token exchange error: {str(e)}")

        elif crm_type.provider == 'jobber':
                url = "https://api.getjobber.com/api/oauth/token"
                data = {
                    'grant_type': 'authorization_code',
                    'client_id': settings.JOBBER_CLIENT_ID,
                    'client_secret': settings.JOBBER_CLIENT_SECRET,
                    'redirect_uri': redirect_uri,
                    'code': code
                }
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
        else:
                logger.error(f"❌ Unsupported CRM provider: {crm_type.provider}")
                return None

        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"❌ Token exchange failed ({crm_type.provider}): {response.text}")
            return None

        
        
    
class DebugZohoTokenView(APIView):
    """Debug view to check Zoho token scopes"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, connection_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        # Check what scopes the token has by calling a simple API
        url = "https://www.zohoapis.com/crm/v2/org"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {connection.oauth_access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return Response({
                    "status": "success", 
                    "scopes": "Token has basic access",
                    "response": response.json()
                })
            else:
                return Response({
                    "status": "error",
                    "code": response.status_code,
                    "message": response.text,
                    "token": connection.oauth_access_token[:50] + "..." if connection.oauth_access_token else None
                })
        except Exception as e:
            return Response({"error": str(e)})

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

from django.http import HttpResponseRedirect


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
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            # form = BusinessDetails.objects.filter(user = feedback.user).first()
            # print("form------------",form)
            # if form:
                # response_data["feedback_url"] = form.form_url
            # response_data["feedback_url"] = f"{settings.FRONTEND_URL}job/feedback/form/{token}/"
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}job/feedback/form/{token}/")
        
        # return Response(response_data, status=status.HTTP_200_OK)
    

# views.py
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer])
def feedback_form_view(request, token):
    """Render feedback form for users who clicked No"""
    feedback = get_object_or_404(ClientFeedback, token=token)
    
    context = {
        'token': token,
        'email': feedback.email,
        'job_id': feedback.job_id,
        'service_area': feedback.service_area
    }
    
    return Response(context, template_name='feedback/feedback_form.html')
# views.py
@api_view(['POST'])
@renderer_classes([JSONRenderer])
def submit_feedback_form(request, token):
    """Handle feedback form submission"""
    feedback = get_object_or_404(ClientFeedback, token=token)
    
    # Update the main feedback record
    feedback.is_satisfied = False
    feedback.save()
    
    # Create form response - pass the feedback instance, not just ID
    form_data = request.data.copy()
    
    # Convert checkbox values from string to boolean
    if 'would_recommend' in form_data:
        form_data['would_recommend'] = form_data['would_recommend'].lower() == 'true'
    
    if 'contact_permission' in form_data:
        form_data['contact_permission'] = form_data['contact_permission'].lower() == 'true'
    
    serializer = FeedbackFormResponseSerializer(data=form_data)
    
    if serializer.is_valid():
        # Save with the feedback instance
        serializer.save(feedback=feedback)
        return Response({
            'success': True,
            'message': 'Thank you for your feedback!'
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)



class AllFeedbackFormResponsesAPIView(APIView):
    """Get ALL feedback form responses (Admin only)"""
    permission_classes = [IsAuthenticated]  # Only admin can access
    
    def get(self, request):
        # Get all feedback form responses with related feedback data
        form_responses = FeedbackFormResponse.objects.all().select_related('feedback')
        
        # Serialize the data
        data = []
        for response in form_responses:
            data.append({
                'id': response.id,
                'satisfaction_level': response.satisfaction_level,
                'satisfaction_level_display': response.get_satisfaction_level_display(),
                'issues_faced': response.issues_faced,
                'suggestions': response.suggestions,
                'would_recommend': response.would_recommend,
                'contact_permission': response.contact_permission,
                'created_at': response.created_at,
                
                # Feedback details
                'feedback_id': response.feedback.id,
                'email': response.feedback.email,
                'job_id': response.feedback.job_id,
                'service_area': response.feedback.service_area,
                'is_satisfied': response.feedback.is_satisfied,
                'feedback_created_at': response.feedback.created_at,
                'user_id': response.feedback.user.id if response.feedback.user else None,
                'user_email': response.feedback.user.email if response.feedback.user else None,
            })
        
        return Response({
            'count': len(data),
            'results': data
        })

class FeedbackFormResponseByIdAPIView(APIView):
    """Get specific feedback form response by ID (Admin only)"""
    permission_classes = [IsAuthenticated]  # Only admin can access
    
    def get(self, request, response_id):
        try:
            response = FeedbackFormResponse.objects.select_related('feedback').get(id=response_id)
            
            data = {
                'id': response.id,
                'satisfaction_level': response.satisfaction_level,
                'satisfaction_level_display': response.get_satisfaction_level_display(),
                'issues_faced': response.issues_faced,
                'suggestions': response.suggestions,
                'would_recommend': response.would_recommend,
                'contact_permission': response.contact_permission,
                'created_at': response.created_at,
                
                # Feedback details
                'feedback_id': response.feedback.id,
                'email': response.feedback.email,
                'job_id': response.feedback.job_id,
                'service_area': response.feedback.service_area,
                'is_satisfied': response.feedback.is_satisfied,
                'feedback_created_at': response.feedback.created_at,
                'user_id': response.feedback.user.id if response.feedback.user else None,
                'user_email': response.feedback.user.email if response.feedback.user else None,
                'crm_connection': response.feedback.crm_connection.connection_name if response.feedback.crm_connection else None,
            }
            
            return Response(data)
            
        except FeedbackFormResponse.DoesNotExist:
            return Response(
                {'error': 'Feedback form response not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

# class CRMJobCreateAPIView(APIView):
#     """Create a job in the connected CRM"""
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request, connection_id):
#         connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
#         if not connection.is_connected:
#             return Response(
#                 {"error": "CRM connection is not active"}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         crm_service = get_crm_service(connection)
#         result = crm_service.create_job(request.data)
        
#         if result['success']:
#             return Response(result, status=status.HTTP_201_CREATED)
#         else:
#             return Response(result, status=status.HTTP_400_BAD_REQUEST)

class CRMJobCreateAPIView(APIView):
    """Create a job in the connected CRM"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active. Please reconnect."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crm_service = get_crm_service(connection)
        result = crm_service.create_job(request.data)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            # Check if it's a scope error that requires re-authentication
            error_msg = result.get('error', '')
            if 're-authenticate' in error_msg.lower() or 'insufficient permissions' in error_msg.lower():
                connection.is_connected = False
                connection.save()
            
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
        

# -------------- Job Tasks 

def extract_keywords_from_job_form(job_form):
    """Extract relevant keywords from JobOnboardingForm fields"""
    keywords = []
    
    # Basic company info
    keywords.extend([
        job_form.company_name,
        "trucking company",
        "CDL jobs",
        "truck driver jobs"
    ])
    
    # Vehicle and equipment keywords
    if job_form.transmission_automatic:
        keywords.append("automatic transmission trucks")
    if job_form.transmission_manual:
        keywords.append("manual transmission trucks")
    if job_form.equip_fridge:
        keywords.append("truck fridge")
    if job_form.equip_inverter:
        keywords.append("power inverter")
    if job_form.equip_microwave:
        keywords.append("microwave equipped")
    if job_form.equip_led:
        keywords.append("LED lighting")
    if job_form.equip_apu:
        keywords.append("APU equipped")
    
    # Job type keywords
    if job_form.position_1099:
        keywords.append("1099 trucking jobs")
    if job_form.position_w2:
        keywords.append("W2 trucking jobs")
    
    # Benefits keywords
    if job_form.benefit_weekly_deposits:
        keywords.append("weekly pay")
    if job_form.referral_bonus:
        keywords.append("referral bonus")
    if job_form.fuel_card:
        keywords.append("fuel card")
    if job_form.detention_layover_pay:
        keywords.append("detention pay")
    if job_form.offer_cash_advances:
        keywords.append("cash advances")
    
    # Area keywords
    if job_form.primary_running_areas:
        areas = job_form.primary_running_areas.split(',')
        for area in areas[:3]:  # Take first 3 areas
            keywords.append(f"trucking jobs {area.strip()}")
            keywords.append(f"CDL jobs {area.strip()}")
    
    # Equipment specifics
    keywords.append(job_form.hauling_equipment)
    keywords.append(f"{job_form.truck_make_year} trucks")
    
    # Clean and deduplicate
    keywords = [k.strip().lower() for k in keywords if k and k.strip()]
    keywords = list(set(keywords))
    
    return keywords[:20]  # Limit to 20 most relevant keywords

def generate_research_questions(keywords):
    """Generate research questions based on keywords"""
    research_words = []
    
    for keyword in keywords:
        # Basic questions about each keyword
        research_words.extend([
            f"What is {keyword}?",
            f"How does {keyword} work in trucking?",
            f"Benefits of {keyword} for truck drivers",
            f"Requirements for {keyword}",
            f"Best practices for {keyword}"
        ])
    
    return research_words[:15]  # Limit research questions

def run_job_blog_writing(task):
    try:
        user = task.user
        
        # Get job onboarding form
        job_onboarding = task.job_onboarding
        if not job_onboarding:
            # Try to get from user if not directly linked to task
            try:
                job_onboarding = user.jobonboardingform
            except:
                job_onboarding = None
        
        if not job_onboarding:
            logger.warning("⚠ No job onboarding form found.")
            task.status = "failed"
            task.save()
            return

        # Monthly check
        current_month = timezone.now().strftime("%Y-%m")
        # onboarding_form = user.onboardingform.last()
        package = getattr(user.usersubscription, "package", None)
        # package = onboarding_form.package
        if not package:
            logger.warning("⚠ No package found for user.")
            task.status = "failed"
            task.save()
            return

        package_limit = package.blog_limit
        
        if task.month_year != current_month:
            task.count_this_month = 0
            task.month_year = current_month

        # Check if limit reached
        if task.count_this_month >= package_limit:
            logger.warning("🚫 Job blog limit reached for this month.")
            task.status = "skipped"
            task.save()
            return

        # Extract keywords from job form
        keywords = extract_keywords_from_job_form(job_onboarding)
        if not keywords:
            logger.warning("⚠ No keywords extracted from job form.")
            task.status = "failed"
            task.save()
            return

        logger.info(f"🔑 Extracted Job Keywords: {keywords}")

        # Generate research questions
        research_words = generate_research_questions(keywords)
        logger.info(f"🧠 Research words: {research_words[:10]}...")

        # Determine area - use primary running areas or company address
        area = "trucking industry"
        if job_onboarding.primary_running_areas:
            areas = job_onboarding.primary_running_areas.split(',')
            area = areas[0].strip() if areas else "trucking industry"
        elif job_onboarding.company_address:
            # Extract city/state from address if possible
            area = "trucking industry"

        # Prepare AI payload
        ai_payload = {
            "keywords": keywords,
            "research_words": research_words,
            "area": area,
            "type": "blog"
        }

        logger.info(f"📤 Sending payload to AI API: {ai_payload}")

        # Call AI API
        response = requests.post(
            f"{settings.AI_API_DOMAIN}/generate_content",
            json=ai_payload,
            timeout=60
        )

        if response.status_code != 200:
            logger.error(f"❌ AI response error: {response.text}")
            task.status = "failed"
            task.ai_request_payload = ai_payload
            task.ai_response_payload = {"error": response.text}
            task.save()
            return
        
        data = response.json()
        blog_html = data.get("content", "").strip()
        image_url = data.get("imageUrl", "")

        # Clean HTML content
        blog_html = re.sub(r"^html\s*", "", blog_html)
        blog_html = re.sub(r"$", "", blog_html.strip())
        
        if not blog_html:
            logger.warning("⚠ Blog content is empty after cleaning.")
            task.status = "failed"
            task.save()
            return

        # Extract title
        soup = BeautifulSoup(blog_html, "html.parser")
        titles = soup.find_all("title")
        title = titles[0].text.strip() if titles else f"{job_onboarding.company_name} Trucking Opportunities"

        logger.info(f"✅ Job Blog generated: {title}")

        # Save blog
        job_blog = JobBlog.objects.create(
            job_task=task,
            title=title,
            content=blog_html
        )
        
         # ✅✅✅ NEW: SAVE THE KEYWORDS TO THE DATABASE
        for keyword_text in keywords:
            JobBlogKeyword.objects.create(job_blog=job_blog, keyword=keyword_text.lower())
        logger.info(f"💾 Saved {len(keywords)} keywords for blog.")

        # ✅ Save image if available
        if image_url:
            JobBlogImage.objects.create(
                job_blog=job_blog,
                image_url=image_url
            )
            logger.info(f"🖼 Job blog image saved: {image_url}")

        # Update task
        task.ai_request_payload = ai_payload
        task.ai_response_payload = data
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=package.interval)
        task.count_this_month += 1
        task.status = "completed"
        task.save()

        logger.info(f"✅ Job Blog Task {task.id} completed successfully.")

        # WordPress upload (you'll provide this function later)
        if hasattr(user, 'wordpress_connection'):
            upload_blog_to_wordpress(job_blog, user.wordpress_connection, is_job_blog=True)

        # Auto-create next task if limit not reached
        if task.count_this_month < package_limit:
            JobTask.objects.create(
                user=user,
                job_onboarding=job_onboarding,
                task_type='job_blog_writing',
                next_run=task.next_run,
                status='pending',
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True
            )
            logger.info(f"✅ New job blog writing task created")
        else:
            JobTask.objects.create(
                user=user,
                job_onboarding=job_onboarding,
                task_type='job_blog_writing',
                next_run=None,
                status='pending',
                count_this_month=0,
                month_year=current_month,
                is_active=True
            )
            logger.info(f"⏸ Job blog limit reached. Next task paused until new month.")

        

    except Exception as e:
        logger.exception(f"❌ Exception in run_job_blog_writing for task {task.id}: {str(e)}")
        task.status = "failed"
        task.ai_response_payload = {"error": str(e)}
        task.save()

    


def map_job_form_to_api_payload(job_form):
    """Map JobOnboardingForm data to the API request payload structure"""
    
    # Determine position type
    # position = "Company Driver"  # Default assumption
    position = job_form.position
    route = job_form.route

    # if not position:
    #     position = 
    #     # Set default based on other fields or logic
    #     if job_form.position_1099 or job_form.position_w2:
    #         position = "Company Driver"
    #   # Generic fallback
    
    pay_type = ""
    # Determine pay type
    if job_form.position_1099 and job_form.position_w2:
        pay_type = "1099 or W2"
    elif job_form.position_1099:
        pay_type = "1099"
    elif job_form.position_w2:
        pay_type = "W2"
    else:
        position = "Driver" 
    
    # Determine pay structure
    pay_structure = ""
    if job_form.cpm:
        pay_structure = f"{job_form.cpm} CPM"
    elif job_form.driver_percentage:
        pay_structure = f"{job_form.driver_percentage}% of load"
    
    # Determine equipment list
    equipment = []
    if job_form.equip_fridge or job_form.main_equip_fridge:
        equipment.append("FRIDGES")
    if job_form.equip_microwave or job_form.main_equip_microwave:
        equipment.append("MICROWAVES")
    if job_form.equip_inverter or job_form.main_equip_inverter:
        equipment.append("INVERTERS")
    if job_form.equip_led or job_form.main_equip_led:
        equipment.append("LED LIGHTING")
    if job_form.equip_apu:
        equipment.append("APU")
    
    # Determine transmission type
    transmission = []
    if job_form.transmission_automatic or job_form.main_auto_transmission:
        transmission.append("AUTOMATIC TRUCKS AVAILABLE")
    if job_form.transmission_manual or job_form.main_manual_transmission:
        transmission.append("MANUAL TRUCKS AVAILABLE")
    
    # Build driver requirements
    driver_requirements = [
        "CDL A LICENSE REQUIRED",
        f"MIN. {job_form.minimum_hiring_age} YEARS OF AGE",
        "Clean Clearinghouse" if job_form.clean_clearinghouse else None,
        "Clean Drug Test" if job_form.clean_drug_test else None
    ]
    
    # Add experience requirement if specified
    if job_form.cdl_experience_required != "3":  # Assuming "3" means 3 months (graduates welcome)
        exp_map = {
            "3": "3 MONTHS",
            "6": "6 MONTHS", 
            "12": "1 YEAR",
            "18": "1.5 YEARS",
            "24": "2 YEARS",
            "36": "3+ YEARS"
        }
        driver_requirements.append(f"MIN. {exp_map.get(job_form.cdl_experience_required, 'EXPERIENCE')} EXPERIENCE")
    else:
        driver_requirements.append("GRADUATES WELCOME")
    
    # Build driver benefits
    driver_benefits = []
    if transmission:
        driver_benefits.extend(transmission)
    
    if job_form.truck_governed_speed:
        driver_benefits.append(f"TRUCKS GOVERNED AT {job_form.truck_governed_speed}")
    
    if job_form.truck_make_year:
        driver_benefits.append(f"FLEET INCLUDES {job_form.truck_make_year}")
    
    if job_form.benefit_weekly_deposits or job_form.main_weekly_deposits:
        driver_benefits.append("WEEKLY DIRECT DEPOSITS")
    
    if job_form.benefit_dispatch_support or job_form.main_dispatch_support:
        driver_benefits.append("24/7 DISPATCH & ROADSIDE ASSISTANCE")
    
    if job_form.main_safety_bonus:
        driver_benefits.append("SAFETY BONUS")
    
    if job_form.referral_bonus or job_form.main_referral_bonus:
        bonus_amount = f" - {job_form.referral_bonus_amount}" if job_form.referral_bonus_amount else ""
        driver_benefits.append(f"REFERRAL BONUS{bonus_amount}")
    
    # Build travel benefits
    travel = []
    if job_form.travel_provided and job_form.travel_description:
        travel.append(job_form.travel_description.upper())
    
    # Build extra information
    extra = []
    if job_form.escrow_required and job_form.escrow_description:
        extra.append(job_form.escrow_description.upper())
    
    # Parse hiring areas from primary_running_areas
    # hiring_area = {
    #     "regions": [],
    #     "states": []
    # }
    
    # if job_form.primary_running_areas:
    #     # Simple parsing - this could be enhanced with more sophisticated logic
    #     areas = job_form.primary_running_areas.split(',')
    #     for area in areas:
    #         area = area.strip()
    #         if len(area) == 2 and area.isupper():  # Likely a state code
    #             hiring_area["states"].append(area)
    #         else:  # Likely a region name
    #             hiring_area["regions"].append(area)

    # if job_form.states:
    #     hiring_area["states"].extend(job_form.states)


    # Parse hiring areas from primary_running_areas
    hiring_area = {
        "regions": [],
        "states": [],
        "radius": None,   # local ke liye
        "type": None      # local / regional / otr
    }

    if job_form.route:  
        route_type = job_form.route.lower().strip()
        
        if route_type == "local":
            hiring_area["type"] = "local"
            # Local case: sirf radius use hogi (map nahi)
            hiring_area["radius"] = job_form.radius if hasattr(job_form, "radius") else None

            hiring_area["regions"] = []
            hiring_area["states"] = []
        
        elif route_type == "regional":
            hiring_area["type"] = "regional"
            if job_form.primary_running_areas:
                areas = job_form.primary_running_areas.split(',')
                for area in areas:
                    area = area.strip()
                    if len(area) == 2 and area.isupper():  # Likely a state code
                        hiring_area["states"].append(area)
                    else:  # Likely a region name
                        hiring_area["regions"].append(area)
            if job_form.states:
                hiring_area["states"].extend(job_form.states)
        
        elif route_type == "otr":
            hiring_area["type"] = "otr"
            # OTR case: full USA map, koi extra filter nahi
            hiring_area["regions"] = ["USA"]

    
    
    # Construct the API payload
    payload = {
        "position": position,
        "route": route,  # Default assumption, could be enhanced
        "hauling": job_form.hauling_equipment.upper() if job_form.hauling_equipment else "VAN",
        "pay_type": pay_type,
        "pay_structure": pay_structure,
        "company_name": job_form.company_name,
        "contact_phone": job_form.contact_phone,
        "contact_email": job_form.hiring_email,
        "website": job_form.company_website or "",
        "terminal_address": job_form.terminal,
        "mc_number": job_form.mc_dot_number.split('/')[0] if '/' in job_form.mc_dot_number else job_form.mc_dot_number,
        "dot_number": job_form.mc_dot_number.split('/')[1] if '/' in job_form.mc_dot_number and len(job_form.mc_dot_number.split('/')) > 1 else "",
        "driver_requirements": [req for req in driver_requirements if req],  # Remove empty strings
        "home_time": job_form.home_time,  # Default assumption
        "driver_benefits": driver_benefits,
        "equipment": equipment,
        "travel": travel,
        "extra": extra,
        "hiring_area": hiring_area
    }
  

    return payload

# def run_job_template_generation(job_onboardingform):
#     try:
#         user = job_onboardingform.user
        
#         # Get job onboarding form
#         job_onboarding = job_onboardingform
#         if not job_onboarding:
#             # Try to get from user if not directly linked to task
#             try:
#                 job_onboarding = user.jobonboardingform
#             except:
#                 job_onboarding = None
        
#         # if not job_onboarding:
#         #     logger.warning("⚠ No job onboarding form found.")
#         #     task.status = "failed"
#         #     task.save()
#         #     return

#         # Monthly check - same logic as before
#         current_month = timezone.now().strftime("%Y-%m")
#         # onboarding_form = user.onboardingform.last()
#         # package = onboarding_form.package
#         package = getattr(user.usersubscription, "package", None)
#         if not package:
#             logger.warning("⚠ No package found for user.")
#             # task.status = "failed"
#             # task.save()
#             # return

#         package_limit = package.blog_limit  # Using same limit as blogs
        
#         # if task.month_year != current_month:
#         #     task.count_this_month = 0
#         #     task.month_year = current_month

#         # Check if limit reached
#         # if task.count_this_month >= package_limit:
#         #     logger.warning("🚫 Job template limit reached for this month.")
#         #     task.status = "skipped"
#         #     task.save()
#         #     return

#         # Map job form data to API payload
#         api_payload = map_job_form_to_api_payload(job_onboarding)
#         logger.info(f"🔑 Generated API payload: {api_payload}")

#         # Call the job template generation API
#         response = requests.post(
#             f"{settings.AI_API_DOMAIN}/generate_job_template",
#             json=api_payload,
#             timeout=60
#         )

#         if response.status_code != 200:
#             logger.error(f"❌ Job template API response error: {response.text}")
#             # task.status = "failed"
#             # task.ai_request_payload = api_payload
#             # task.ai_response_payload = {"error": response.text}
#             # task.save()
#             return
        
#         data = response.json()
#         job_template = data.get("jobTemplate", "").strip()
        
#         if not job_template:
#             logger.warning("⚠ Job template is empty.")
#             # task.status = "failed"
#             # task.save()
#             return

#         logger.info(f"✅ Job Template generated successfully")

#                 # Add cost structure to the AI response if applicable
#         if job_onboarding.position and job_onboarding.position.lower() in ["owner operator", "lease-to-rent", "lease-to-purchase"]:
#             cost_structure = map_cost_structure(job_onboarding)
#             data["cost_structure"] = cost_structure
#             logger.info(f"✅ Added cost structure to response: {cost_structure}")

#         # Save the template (you might want to create a new model for this)
#         # For now, we'll update the task with the response
#         # task.ai_request_payload = api_payload
#         # task.ai_response_payload = data
#         # task.last_run = timezone.now()
#         # task.next_run = timezone.now() + timedelta(days=package.interval)
#         # task.count_this_month += 1
#         # task.status = "completed"
#         # task.save()

#         logger.info(f"✅ Job Template Task completed successfully.")

#         # WordPress upload - convert the template to HTML and post
#         if hasattr(user, 'wordpress_connection'):
#             # Convert the template text to HTML
#             # html_content = convert_template_to_html(job_template)
#             html_content = process_job_template_html(job_template)
#             # html_content = f"<div>{job_template.replace('**', '<strong>').replace('*', '<li>').replace('\n', '<br>')}</div>"
#             upload_job_post_to_wordpress(job_onboarding, user.wordpress_connection, html_content,api_payload=data)

#         # Auto-create next task if limit not reached - same logic as before
#         # if task.count_this_month < package_limit:
#         #     JobTask.objects.create(
#         #         user=user,
#         #         job_onboarding=job_onboarding,
#         #         task_type='job_template_generation',  # Or create a new task type for templates
#         #         next_run=task.next_run,
#         #         status='pending',
#         #         count_this_month=task.count_this_month,
#         #         month_year=current_month,
#         #         is_active=True
#         #     )
#             logger.info(f"✅ New job template task created")
#         # else:
#         #     JobTask.objects.create(
#         #         user=user,
#         #         job_onboarding=job_onboarding,
#         #         task_type='job_template_generation',  # Or create a new task type for templates
#         #         next_run=None,
#         #         status='pending',
#         #         count_this_month=0,
#         #         month_year=current_month,
#         #         is_active=True
#         #     )
#             logger.info(f"⏸ Job template limit reached. Next task paused until new month.")

#     except Exception as e:
#         logger.exception(f"❌ Exception in run_job_template_generation for task: {str(e)}")
#         # task.status = "failed"
#         # task.ai_response_payload = {"error": str(e)}
#         # task.save()




# test
def run_job_template_generation(job_task_or_form, is_update=False):
    try:
        if isinstance(job_task_or_form, JobTask):
            job_onboarding = job_task_or_form.job_onboarding
            user = job_task_or_form.user
        else:
            job_onboarding = job_task_or_form
            user = job_onboarding.user

        if not job_onboarding:
            logger.warning("⚠ No job onboarding form found.")
            return

        # For updates, find the existing template instead of creating a new one
        if is_update:
            job_template = JobTemplate.objects.filter(
                job_onboarding=job_onboarding
            ).order_by('-created_at').first()
            
            if not job_template:
                logger.warning("No existing job template found for update.")
                # Fallback to creating a new one if no existing template found
                job_template = JobTemplate.objects.create(
                    user=user,
                    job_onboarding=job_onboarding,
                    status='processing'
                )
            else:
                job_template.status = 'processing'
        else:
            # Create new template for new submissions
            job_template = JobTemplate.objects.create(
                user=user,
                job_onboarding=job_onboarding,
                status='processing'
            )

        # Map job form data
        api_payload = map_job_form_to_api_payload(job_onboarding)
        job_template.ai_request_payload = api_payload
        job_template.save()
        
        response = requests.post(
            f"{settings.AI_API_DOMAIN}/generate_job_template",
            json=api_payload,
            timeout=60
        )
        
        if response.status_code != 200:
            logger.error(f"❌ API error: {response.text}")
            job_template.status = 'failed'
            job_template.save()
            return
        
        data = response.json()
        job_template_content = data.get("jobTemplate", "").strip()

        if not job_template_content:
            logger.warning("⚠ Empty job template.")
            job_template.status = 'failed'
            job_template.save()
            return
        
        # Update job template with AI response
        job_template.ai_response_payload = data
        job_template.generated_content = job_template_content

        if job_onboarding.position and job_onboarding.position.lower() in ["owner operator", "lease-to-rent", "lease-to-purchase"]:
            cost_structure = map_cost_structure(job_onboarding)
            data["cost_structure"] = cost_structure
            logger.info(f"✅ Added cost structure to response: {cost_structure}")

        # WordPress upload/update
        if hasattr(user, 'wordpress_connection'):
            html_content = process_job_template_html(job_template_content)
            
            # For updates, use the existing page ID if available
            page_id = job_template.wp_page_id if is_update else None
            page_url = upload_job_post_to_wordpress(
                job_onboarding,
                user.wordpress_connection,
                html_content,
                api_payload=data,
                page_id=page_id,  # Pass page_id for updates
                job_template=job_template  # Pass the job template
            )

            if page_url:
                job_template.wp_page_url = page_url
                job_template.status = 'completed'
                job_template.published_date = timezone.now()
                logger.info(f"✅ Job {'updated' if is_update else 'uploaded'} for {job_onboarding.company_name}")
            else:
                job_template.status = 'failed'
        
        job_template.save()
        return job_template

    except Exception as e:
        logger.exception(f"❌ Error in run_job_template_generation: {str(e)}")
        if job_template:
            job_template.status = 'failed'
            job_template.save()
        return None



# Update the task creation function to handle template generation
def create_initial_job_tasks(user, job_onboarding):
    # onboarding_form = user.onboardingform.last()
    # if not onboarding_form or not onboarding_form.package:
    #     return None

    package = getattr(user, "usersubscription", None)
    if package:
        package = package.package
    current_month = timezone.now().strftime("%Y-%m")
    
    # Create blog task
    blog_task = JobTask.objects.create(
        user=user,
        job_onboarding=job_onboarding,
        task_type='job_blog_writing',
        next_run=timezone.now(),
        status='pending',
        count_this_month=0,
        month_year=current_month,
        is_active=True
    )
    
    # Create template task
    # template_task = JobTask.objects.create(
    #     user=user,
    #     job_onboarding=job_onboarding,
    #     task_type='job_template_generation',  # You might need to add this to TASK_TYPES
    #     next_run=timezone.now(),
    #     status='pending',
    #     count_this_month=0,
    #     month_year=current_month,
    #     is_active=True
    # )
    
    logger.info(f"✅ Initial job tasks created for user {user.email}")
    return blog_task
    


# -------------------
from rest_framework.pagination import PageNumberPagination
import math
class JobPostsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.count = queryset.count()
        self.page_size = self.get_page_size(request) or self.page_size

        try:
            return super().paginate_queryset(queryset, request, view=view)
        except Exception:
            # If page is invalid, don't break — return empty list
            self.page = None
            return []

    def get_paginated_response(self, data):
        total_items = self.count
        page_size = self.page_size
        total_pages = math.ceil(total_items / page_size) if page_size else 1
        current_page = (
            self.page.number if self.page else int(self.request.query_params.get("page", 1))
        )

        return Response({
            "success": True,
            "message": "Job posts retrieved successfully.",
            "pagination": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": current_page,
                "page_size": page_size,
            },
            "data": data if data is not None else [],
        })


from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

from .models import JobTemplate
from .serializers import JobTemplateSerializer

class MyJobPostsView(APIView):
    permission_classes = [IsAuthenticated]

    # def get(self, request, pk=None):
    #     if pk is None:
    #         job_tasks = JobTask.objects.filter(
    #             user=request.user,
    #             task_type="job_template_generation"
    #         ).order_by("-created_at")

    #         paginator = JobPostsPagination()
    #         result_page = paginator.paginate_queryset(job_tasks, request)
    #         serializer = JobTaskSerializer(result_page, many=True)

    #         # ✅ send serializer.data directly
    #         return paginator.get_paginated_response(serializer.data)

    #     # Single job post retrieval
    #     job_task = JobTask.objects.filter(
    #         user=request.user,
    #         task_type="job_template_generation",
    #         pk=pk
    #     ).first()

    #     if not job_task:
    #         return Response({
    #             "success": False,
    #             "message": "Job post not found.",
    #             "data": None,
    #         }, status=status.HTTP_404_NOT_FOUND)

    #     serializer = JobTaskSerializer(job_task)
    #     return Response({
    #         "success": True,
    #         "message": "Job post retrieved successfully.",
    #         "data": serializer.data,
    #     }, status=status.HTTP_200_OK)

    def get(self, request, pk=None):
        if pk is None:
            # Get all job templates for the user
            job_templates = JobTemplate.objects.filter(
                user=request.user
            ).order_by("-created_at")
            
            # Pagination
            paginator = JobPostsPagination()
            result_page = paginator.paginate_queryset(job_templates, request)
            serializer = JobTemplateSerializer(result_page, many=True)

            # ✅ send serializer.data directly
            return paginator.get_paginated_response(serializer.data)
            
        

        # Single job post retrieval
        job_template = JobTemplate.objects.filter(
            user=request.user,
            pk=pk
        ).first()

        if not job_template:
            return Response({
                "success": False,
                "message": "Job post not found.",
                "data": None,
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = JobTemplateSerializer(job_template)
        return Response({
            "success": True,
            "message": "Job post retrieved successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)






class MyJobBlogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        job_blogs = JobBlog.objects.filter(job_task__user=request.user)
        serializer = JobBlogSerializer(job_blogs, many=True)
        return Response({
            "success": True, 
            "message": "Job blogs retrieved successfully.", 
            "blog_count": job_blogs.count(),
            "data": serializer.data
        })
    

class JobPostCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Count job tasks (job posts) for the logged-in user
        total_job_posts = JobTask.objects.filter(
            # user=request.user,
            task_type='job_template_generation'  # same task type as your listing
        ).count()

        return Response({
            "success": True,
            "message": "Total job posts retrieved successfully.",
            "total_job_posts": total_job_posts
        })
    


from django.db.models import Count
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response

class JobStatsAPIView(APIView):
    permission_classes = [IsAdminUser]  # Only admin can access

    def get(self, request):
        # Total users
        total_users = User.objects.filter(user_type="user").count()

        # Total job posts
        total_job_posts = JobTask.objects.filter(task_type="job_template_generation").count()

        # Latest job blogs (last 5)
        latest_job_blogs = JobBlog.objects.order_by("-created_at")[:5]
        latest_job_blogs_data = JobBlogSerializer(latest_job_blogs, many=True).data

        return Response({
            "total_users": total_users,
            "total_job_posts": total_job_posts,
            "latest_job_blogs": latest_job_blogs_data
        })





# api/views.py
from django.db.models import Q
from urllib.parse import urlparse
from datetime import datetime, timedelta
from django.utils import timezone
from googleapiclient.errors import HttpError


class JobContentMetricsView(APIView):
    """
    API to fetch Search Console metrics for all published Job Blogs and Job Postings (JobTasks)
    for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            token = SearchConsoleToken.objects.get(user=user)
        except SearchConsoleToken.DoesNotExist:
            return Response({"error": "Search Console not connected"}, status=400)

        # 1. Get all Job Blogs with URLs
        job_blogs = JobBlog.objects.filter(
            job_task__user=user,
            wp_post_url__isnull=False
        ).exclude(wp_post_url='')
        # 2. Get all Job Posting TASKS with URLs
        job_posting_tasks = JobTask.objects.filter(
            user=user,
            task_type='job_template_generation', # Only get job posting tasks
            wp_page_url__isnull=False
        ).exclude(wp_page_url='')

        # Combine all URLs from both models
        all_urls = [blog.wp_post_url for blog in job_blogs] + [task.wp_page_url for task in job_posting_tasks]

        if not all_urls:
            return Response({"message": "No published job blogs or postings found."}, status=200)

        service = build_service(token.credentials)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        # Handle the siteUrl format (domain vs. URL-prefix)
        if token.site_url.startswith('sc-domain:'):
            domain = token.site_url.replace('sc-domain:', 'https://')
        else:
            domain = token.site_url.rstrip('/')

        # Build full URL expressions for the API query
        page_expressions = []
        for url in all_urls:
            parsed = urlparse(url)
            if parsed.netloc:
                page_expressions.append(url)
            else:
                page_expressions.append(f"{domain}{parsed.path}")

        page_expressions = list(set(page_expressions))
        print(f"Querying GSC for Job Content URLs: {page_expressions}")

        try:
            response = service.searchanalytics().query(
                siteUrl=token.site_url,
                body={
                    'startDate': start_date.strftime('%Y-%m-%d'),
                    'endDate': end_date.strftime('%Y-%m-%d'),
                    'dimensions': ['page'],
                    'rowLimit': 10000,
                    'dimensionFilterGroups': [{
                        'filters': [{
                            'dimension': 'page',
                            'operator': 'equals',
                            'expression': expr
                        } for expr in page_expressions]
                    }]
                }
            ).execute()

            updated_records = []
            if 'rows' in response:
                for row in response.get('rows', []):
                    page_url_from_gsc = row['keys'][0]
                    clicks = row.get('clicks', 0)
                    impressions = row.get('impressions', 0)
                    ctr = row.get('ctr', 0)

                    # Try to find a matching JobBlog
                    for blog in job_blogs:
                        if self._urls_match(blog.wp_post_url, page_url_from_gsc, domain):
                            blog.clicks = clicks
                            blog.impressions = impressions
                            blog.ctr = ctr
                            blog.last_metrics_update = timezone.now()
                            blog.save()
                            updated_records.append({'type': 'JobBlog', 'id': blog.id, 'title': blog.title, 'url': blog.wp_post_url})
                            break
                    else:
                        # If no JobBlog was found, try to find a matching JobTask (Job Posting)
                        for task in job_posting_tasks:
                            if self._urls_match(task.wp_page_url, page_url_from_gsc, domain):
                                task.clicks = clicks
                                task.impressions = impressions
                                task.ctr = ctr
                                task.last_metrics_update = timezone.now()
                                task.save()
                                updated_records.append({'type': 'JobPosting', 'id': task.id, 'title': f"Job Post #{task.id}", 'url': task.wp_page_url})
                                break

            return Response({
                'updated_count': len(updated_records),
                'updated_records': updated_records,
                'queried_expressions': page_expressions,
                'found_rows': len(response.get('rows', []))
            })

        except Exception as e:
            return Response({"error": f"Search Console API Error: {str(e)}"}, status=500)

    def _urls_match(self, stored_url, gsc_url, domain):
        parsed_stored = urlparse(stored_url)
        parsed_gsc = urlparse(gsc_url)
        # Simple matching: compare the path part of the URL
        return parsed_stored.path == parsed_gsc.path
    



class SyncJobKeywordsView(APIView):
    """
    API to trigger synchronization of Search Console data for Job Blog keywords.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = sync_job_keywords(request.user)
        if 'error' in result:
            return Response(result, status=500)
        return Response(result)
    


# # api/views.py
# class JobContentMetricsView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         try:
#             token = SearchConsoleToken.objects.get(user=user)
#         except SearchConsoleToken.DoesNotExist:
#             return Response({"error": "Search Console not connected"}, status=400)

#         # ... [Code to fetch job_blogs and job_posting_tasks] ...
#         # 1. Get all Job Blogs with URLs
#         job_blogs = JobBlog.objects.filter(
#             job_task__user=user,
#             wp_post_url__isnull=False
#         ).exclude(wp_post_url='')
#         # 2. Get all Job Posting TASKS with URLs
#         job_posting_tasks = JobTask.objects.filter(
#             user=user,
#             task_type='job_template_generation', # Only get job posting tasks
#             wp_page_url__isnull=False
#         ).exclude(wp_page_url='')
#         all_urls = [blog.wp_post_url for blog in job_blogs] + [task.wp_page_url for task in job_posting_tasks]

#         if not all_urls:
#             return Response({"message": "No published job blogs or postings found."}, status=200)

#         service = build_service(token.credentials)
#         end_date = timezone.now().date()
#         start_date = end_date - timedelta(days=90)  # Increased to 90 days for testing

#         # Build expressions based on property type
#         page_expressions = []
#         for url in all_urls:
#             parsed = urlparse(url)
#             # CRITICAL FIX: Use path for domain properties, full URL for URL-prefix properties
#             if token.site_url.startswith('sc-domain:'):
#                 expression = parsed.path  # e.g., '/local-owner-operator.../'
#             else:
#                 # For URL-prefix properties, use the full URL from the database
#                 expression = url
#             page_expressions.append(expression)

#         page_expressions = list(set(page_expressions))
#         print(f"Querying GSC for expressions: {page_expressions}")
#         print(f"Using siteUrl: {token.site_url}")
#         print(f"Date range: {start_date} to {end_date}")

#         try:
#             body = {
#                 'startDate': start_date.strftime('%Y-%m-%d'),
#                 'endDate': end_date.strftime('%Y-%m-%d'),
#                 'dimensions': ['page'],
#                 'rowLimit': 10000,
#                 'dimensionFilterGroups': [{
#                     'filters': [{
#                         'dimension': 'page',
#                         'operator': 'equals', # Start with 'equals', try 'contains' if this fails
#                         'expression': expr
#                     } for expr in page_expressions]
#                 }]
#             }
#             print(f"Request Body: {body}") # Debug the final request

#             response = service.searchanalytics().query(
#                 siteUrl=token.site_url,
#                 body=body
#             ).execute()

#             print(f"GSC API Response: {response}") # Log the full response

#             updated_records = []
#             found_rows = response.get('rows', [])
#             if found_rows:
#                 print(f"Found {len(found_rows)} rows of data.")
#                 for row in found_rows:
#                     page_url_from_gsc = row['keys'][0]
#                     clicks = row.get('clicks', 0)
#                     impressions = row.get('impressions', 0)
#                     ctr = row.get('ctr', 0)
#                     print(f"Processing GSC row: {page_url_from_gsc}, Clicks: {clicks}")

#                     # ... [Your existing logic to update JobBlog and JobTask] ...
#             else:
#                 print("GSC returned no data (rows not found in response).")

#             return Response({
#                 'updated_count': len(updated_records),
#                 'updated_records': updated_records,
#                 'queried_expressions': page_expressions,
#                 'found_rows': len(found_rows),
#                 'debug': {
#                     'siteUrl': token.site_url,
#                     'date_range': f"{start_date} to {end_date}"
#                 }
#             })

#         except HttpError as e:
#             error_details = json.loads(e.content.decode())
#             print(f"Google API Error: {error_details}")
#             return Response({"error": "Google API Error", "details": error_details}, status=500)
#         except Exception as e:
#             print(f"Other Error: {str(e)}")
#             return Response({"error": f"Search Console Sync Error: {str(e)}"}, status=500)



# # api/views.py
# class JobContentMetricsView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         try:
#             token = SearchConsoleToken.objects.get(user=user)
#         except SearchConsoleToken.DoesNotExist:
#             return Response({"error": "Search Console not connected"}, status=400)

#         # ... [Code to fetch job_blogs and job_posting_tasks] ...
#         #         # 1. Get all Job Blogs with URLs
#         job_blogs = JobBlog.objects.filter(
#             job_task__user=user,
#             wp_post_url__isnull=False
#         ).exclude(wp_post_url='')
#         # 2. Get all Job Posting TASKS with URLs
#         job_posting_tasks = JobTask.objects.filter(
#             user=user,
#             task_type='job_template_generation', # Only get job posting tasks
#             wp_page_url__isnull=False
#         ).exclude(wp_page_url='')
#         all_urls = [blog.wp_post_url for blog in job_blogs] + [task.wp_page_url for task in job_posting_tasks]

#         if not all_urls:
#             return Response({"message": "No published job blogs or postings found."}, status=200)

#         service = build_service(token.credentials)
#         end_date = timezone.now().date()
#         start_date = end_date - timedelta(days=90)

#         # Build expressions based on property type
#         page_expressions = []
#         for url in all_urls:
#             parsed = urlparse(url)
#             if token.site_url.startswith('sc-domain:'):
#                 expression = parsed.path
#             else:
#                 expression = url
#             page_expressions.append(expression)

#         page_expressions = list(set(page_expressions))
#         print(f"Querying GSC for expressions: {page_expressions}")

#         try:
#             # Let's try a more flexible approach: check each URL one-by-one
#             # and use 'contains' instead of 'equals' to catch variations
#             all_rows = []
#             for expr in page_expressions:
#                 body = {
#                     'startDate': start_date.strftime('%Y-%m-%d'),
#                     'endDate': end_date.strftime('%Y-%m-%d'),
#                     'dimensions': ['page'],
#                 }
#                 # Try a 'contains' filter for better matching
#                 body['dimensionFilterGroups'] = [{
#                     'filters': [{
#                         'dimension': 'page',
#                         'operator': 'contains', # CHANGED FROM 'equals' TO 'contains'
#                         'expression': expr
#                     }]
#                 }]

#                 print(f"Testing expression: {expr}")
#                 response = service.searchanalytics().query(
#                     siteUrl=token.site_url,
#                     body=body
#                 ).execute()
#                 if 'rows' in response:
#                     all_rows.extend(response['rows'])

#             print(f"Total rows found across all queries: {len(all_rows)}")

#             updated_records = []
#             if all_rows:
#                 for row in all_rows:
#                     page_url_from_gsc = row['keys'][0]
#                     clicks = row.get('clicks', 0)
#                     impressions = row.get('impressions', 0)
#                     ctr = row.get('ctr', 0)
#                     print(f"Data found for: {page_url_from_gsc} (Clicks: {clicks}, Impressions: {impressions})")

#                     # ... [Your existing logic to update JobBlog and JobTask] ...
#                     # Try to find a matching JobBlog
#                     for blog in job_blogs:
#                         if self._urls_match(blog.wp_post_url, page_url_from_gsc, domain):
#                             blog.clicks = clicks
#                             blog.impressions = impressions
#                             blog.ctr = ctr
#                             blog.last_metrics_update = timezone.now()
#                             blog.save()
#                             updated_records.append({'type': 'JobBlog', 'id': blog.id, 'title': blog.title, 'url': blog.wp_post_url})
#                             break
#                     else:
#                         # If no JobBlog was found, try to find a matching JobTask (Job Posting)
#                         for task in job_posting_tasks:
#                             if self._urls_match(task.wp_page_url, page_url_from_gsc, domain):
#                                 task.clicks = clicks
#                                 task.impressions = impressions
#                                 task.ctr = ctr
#                                 task.last_metrics_update = timezone.now()
#                                 task.save()
#                                 updated_records.append({'type': 'JobPosting', 'id': task.id, 'title': f"Job Post #{task.id}", 'url': task.wp_page_url})
#                             break

#             return Response({
#                 'updated_count': len(updated_records),
#                 'updated_records': updated_records,
#                 'queried_expressions': page_expressions,
#                 'found_rows': len(all_rows),
#                 'debug': {
#                     'siteUrl': token.site_url,
#                     'date_range': f"{start_date} to {end_date}",
#                     'message': 'No data found in GSC for the given paths. The pages may be new, not indexed, or have no impressions yet.'
#                 }
#             })

#         except HttpError as e:
#             error_details = json.loads(e.content.decode())
#             print(f"Google API Error: {error_details}")
#             return Response({"error": "Google API Error", "details": error_details}, status=500)
#         except Exception as e:
#             print(f"Other Error: {str(e)}")
#             return Response({"error": f"Search Console Sync Error: {str(e)}"}, status=500)
# api/views.py
from django.db.models import Sum, Avg, Count, Q

class JobPerformanceDashboardView(APIView):
    """
    API to get a summary of performance metrics for all job-related content.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get aggregates for Job Blogs
        blog_metrics = JobBlog.objects.filter(
            job_task__user=user
        ).aggregate(
            total_count=Count('id'),
            total_clicks=Sum('clicks'),
            total_impressions=Sum('impressions'),
            avg_ctr=Avg('ctr')
        )

        # Get aggregates for Job Posting Tasks
        posting_metrics = JobTask.objects.filter(
            user=user,
            task_type='job_template_generation'
        ).aggregate(
            total_count=Count('id'),
            total_clicks=Sum('clicks'),
            total_impressions=Sum('impressions'),
            avg_ctr=Avg('ctr')
        )

        # Get top performing content
        top_blogs = JobBlog.objects.filter(job_task__user=user).order_by('-clicks')[:5].values(
            'id', 'title', 'clicks', 'impressions', 'ctr', 'wp_post_url'
        )
        top_postings = JobTask.objects.filter(
            user=user, task_type='job_template_generation'
        ).order_by('-clicks')[:5].values(
            'id', 'wp_page_url', 'clicks', 'impressions', 'ctr'
        )
        # Add a title for postings
        for post in top_postings:
            post['title'] = f"Job Post #{post['id']}"

        response_data = {
            "summary": {
                "job_blogs": blog_metrics,
                "job_postings": posting_metrics,
            },
            "top_performing": {
                "blogs": top_blogs,
                "postings": top_postings,
            }
        }

        return Response(response_data)
    

# api/views.py
from django.db.models import Q
from urllib.parse import urlparse

class JobContentAnalyticsView(APIView):
    """
    API to fetch Google Analytics 4 data specifically for published Job Blogs and Job Postings.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            # 1. Get the user's GA4 token and property ID
            try:
                token = GoogleAnalyticsToken.objects.get(user=user)
            except GoogleAnalyticsToken.DoesNotExist:
                return Response({"error": "Google Analytics not connected."}, status=400)

            if not token.property_id:
                return Response({"error": "Google Analytics property not set."}, status=400)

            # 2. Get all URLs we want to filter for
            job_blogs = JobBlog.objects.filter(job_task__user=user, wp_post_url__isnull=False).exclude(wp_post_url='')
            job_posting_tasks = JobTask.objects.filter(user=user, task_type='job_template_generation', wp_page_url__isnull=False).exclude(wp_page_url='')
            
            all_urls = [blog.wp_post_url for blog in job_blogs] + [task.wp_page_url for task in job_posting_tasks]
            
            if not all_urls:
                return Response({"message": "No published job blogs or postings found."}, status=200)

            # Extract just the paths for filtering
            page_paths = []
            for url in all_urls:
                parsed = urlparse(url)
                page_paths.append(parsed.path) # e.g., '/local-owner-operator.../'

            page_paths = list(set(page_paths))
            print(f"Fetching Analytics for paths: {page_paths}")

            headers = {
                "Authorization": f"Bearer {token.access_token}",
                "Content-Type": "application/json"
            }

            # 3. Prepare the GA4 API Request Body
            # We filter specifically for the page paths of our job content
            analytics_body = {
                "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
                "metrics": [
                    {"name": "screenPageViews"},
                    {"name": "userEngagementDuration"}, # Total time spent on these pages
                    {"name": "engagedSessions"},
                    {"name": "averageSessionDuration"}, # Avg. session duration
                    {"name": "bounceRate"},
                ],
                "dimensions": [
                    {"name": "pagePath"}, # We group by the page path
                    {"name": "pageTitle"},
                ],
                "dimensionFilter": {
                    "filter": {
                        "fieldName": "pagePath",
                        "inListFilter": {
                            "values": page_paths,
                        }
                    }
                }
            }

            analytics_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{token.property_id}:runReport"
            analytics_resp = requests.post(analytics_url, headers=headers, json=analytics_body)
            
            if analytics_resp.status_code != 200:
                return Response({"error": "Analytics API error", "details": analytics_resp.json()}, status=analytics_resp.status_code)

            analytics_data = analytics_resp.json().get("rows", [])
            print(f"Found {len(analytics_data)} rows in Analytics API response.")

            updated_records = []
            # 4. Process the response and update our models
            for row in analytics_data:
                dimension_vals = row.get('dimensionValues', [])
                metric_vals = row.get('metricValues', [])
                
                if not dimension_vals or not metric_vals:
                    continue
                    
                page_path = dimension_vals[0].get('value') # e.g., '/local-owner-operator.../'
                page_title = dimension_vals[1].get('value', 'N/A')
                
                page_views = int(metric_vals[0].get('value', 0))
                total_engagement_time = float(metric_vals[1].get('value', 0)) # Total seconds
                engaged_sessions = int(metric_vals[2].get('value', 0))
                avg_session_duration = float(metric_vals[3].get('value', 0))
                bounce_rate = float(metric_vals[4].get('value', 0)) # Already a decimal (0.XX)

                # Calculate Average Time on Page (Total engagement time / Number of page views)
                avg_time_on_page = round(total_engagement_time / page_views, 2) if page_views > 0 else 0

                print(f"Processing Analytics for: {page_path} | Views: {page_views} | Avg Time: {avg_time_on_page}s")

                # Find the corresponding model object and update it
                # Check JobBlogs first
                for blog in job_blogs:
                    parsed_blog_url = urlparse(blog.wp_post_url)
                    if parsed_blog_url.path == page_path:
                        blog.ga4_page_views = page_views
                        blog.ga4_avg_time_on_page = avg_time_on_page
                        blog.ga4_bounce_rate = bounce_rate
                        blog.save()
                        updated_records.append({'type': 'JobBlog', 'id': blog.id, 'title': blog.title})
                        break
                else:
                    # If not a blog, check Job Posting Tasks
                    for task in job_posting_tasks:
                        parsed_task_url = urlparse(task.wp_page_url)
                        if parsed_task_url.path == page_path:
                            task.ga4_page_views = page_views
                            task.ga4_avg_time_on_page = avg_time_on_page
                            task.ga4_bounce_rate = bounce_rate
                            task.save()
                            updated_records.append({'type': 'JobPosting', 'id': task.id})
                            break

            return Response({
                'updated_count': len(updated_records),
                'updated_records': updated_records,
                'analytics_rows_found': len(analytics_data),
                'queried_paths': page_paths
            })

        except Exception as e:
            print(f"Error in JobContentAnalyticsView: {str(e)}")
            return Response({"error": str(e)}, status=500)


# ==================== Jobber CRM Contact Operations ====================

class JobberContactCreateAPIView(APIView):
    """Create a contact in Jobber CRM"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active. Please reconnect."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if connection.crm_type.provider != 'jobber':
            return Response(
                {"error": "This endpoint is only for Jobber CRM connections"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crm_service = get_crm_service(connection)
        result = crm_service.create_contact(request.data)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            # Check if it's a scope error that requires re-authentication
            error_msg = result.get('error', '')
            if 're-authenticate' in error_msg.lower() or 'insufficient permissions' in error_msg.lower():
                connection.is_connected = False
                connection.save()
            
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class JobberContactUpdateAPIView(APIView):
    """Update a contact in Jobber CRM"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, connection_id, contact_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active. Please reconnect."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if connection.crm_type.provider != 'jobber':
            return Response(
                {"error": "This endpoint is only for Jobber CRM connections"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crm_service = get_crm_service(connection)
        result = crm_service.update_contact(contact_id, request.data)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            # Check if it's a scope error that requires re-authentication
            error_msg = result.get('error', '')
            if 're-authenticate' in error_msg.lower() or 'insufficient permissions' in error_msg.lower():
                connection.is_connected = False
                connection.save()
            
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class JobberContactListAPIView(APIView):
    """List contacts from Jobber CRM"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, connection_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active. Please reconnect."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if connection.crm_type.provider != 'jobber':
            return Response(
                {"error": "This endpoint is only for Jobber CRM connections"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get pagination parameters
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        
        crm_service = get_crm_service(connection)
        result = crm_service.list_contacts(limit=limit, offset=offset)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            # Check if it's a scope error that requires re-authentication
            error_msg = result.get('error', '')
            if 're-authenticate' in error_msg.lower() or 'insufficient permissions' in error_msg.lower():
                connection.is_connected = False
                connection.save()
            
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class JobberJobCreateAPIView(APIView):
    """Create a job in Jobber CRM"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active. Please reconnect."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if connection.crm_type.provider != 'jobber':
            return Response(
                {"error": "This endpoint is only for Jobber CRM connections"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crm_service = get_crm_service(connection)
        result = crm_service.create_job(request.data)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            # Check if it's a scope error that requires re-authentication
            error_msg = result.get('error', '')
            if 're-authenticate' in error_msg.lower() or 'insufficient permissions' in error_msg.lower():
                connection.is_connected = False
                connection.save()
            
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class JobberJobCloseAPIView(APIView):
    """Close a job in Jobber CRM"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id, job_id):
        connection = get_object_or_404(CRMConnection, id=connection_id, user=request.user)
        
        if not connection.is_connected:
            return Response(
                {"error": "CRM connection is not active"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if connection.crm_type.provider != 'jobber':
            return Response(
                {"error": "This endpoint is only for Jobber CRM connections"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        won = request.data.get('won', True)
        crm_service = get_crm_service(connection)
        result = crm_service.close_job(job_id, won)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)