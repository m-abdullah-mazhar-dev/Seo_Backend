# serializers.py

from venv import logger
from rest_framework import serializers

from job.utility import fetch_wordpress_post_data
from .models import *
from django.utils.html import strip_tags

class JobOnboardingFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOnboardingForm
        fields = '__all__'
        read_only_fields = ['user']

class CRMTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMType
        fields = '__all__'

class CRMConnectionSerializer(serializers.ModelSerializer):
    crm_type_name = serializers.CharField(source='crm_type.name', read_only=True)
    is_token_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CRMConnection
        fields = '__all__'
        read_only_fields = ('user', 'webhook_secret_token', 'webhook_url', 
                           'oauth_access_token', 'oauth_refresh_token', 'oauth_token_expiry')
    
    def validate(self, data):
        crm_type = data.get('crm_type')
        api_key = data.get('api_key')
        api_domain = data.get('api_domain')
        
        if crm_type:
            if crm_type.auth_type in ['api_key', 'both'] and not api_key:
                raise serializers.ValidationError(
                    {"api_key": "API key is required for this CRM type"}
                )
            
            # For Pipedrive, we need both API key and domain
            if crm_type.provider == 'pipedrive' and not api_domain:
                raise serializers.ValidationError(
                    {"api_domain": "API domain is required for Pipedrive"}
                )
        
        return data

class OAuthInitSerializer(serializers.Serializer):
    crm_type_id = serializers.IntegerField()
    # redirect_uri = serializers.URLField()

class OAuthCallbackSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField()

class ClientFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientFeedback
        fields = '__all__'
    






class JobBlogImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobBlogImage
        fields = ['image_url', 'uploaded_at']

class JobBlogSerializer(serializers.ModelSerializer):
    images = JobBlogImageSerializer(many=True, read_only=True)
    category = serializers.CharField(source="job_task.task_type", read_only=True)
    posted_on = serializers.DateTimeField(source="created_at", read_only=True)
    description = serializers.SerializerMethodField()

    class Meta:
        model = JobBlog
        fields = ['id', 'title', 'content', 'category', 'posted_on', 'wp_post_id','wp_post_url','wp_status', 'description' , 'images']
    
    
    def get_description(self, obj):
        plain_text = strip_tags(obj.content)  # remove <p>, <h1>, etc.
        return plain_text[:200] + "..." if plain_text else None


# class JobTaskSerializer(serializers.ModelSerializer):
#     job_title = serializers.SerializerMethodField()
#     job_description = serializers.SerializerMethodField()
#     posted_on = serializers.DateTimeField(source="created_at", read_only=True)
#     total_applicants = serializers.SerializerMethodField()  # You'll need to implement this

#     class Meta:
#         model = JobTask
#         fields = ['id', 'job_title', 'job_description', 'posted_on', 'total_applicants', 'status']

#     def get_job_title(self, obj):
#         # Extract job title from the AI response payload
#         if obj.ai_response_payload and 'jobTemplate' in obj.ai_response_payload:
#             # You might want to parse the template to extract a proper title
#             return f"{obj.job_onboarding.company_name} - Driver Position"
#         return "Job Position"

#     def get_job_description(self, obj):
#         # Return the first part of the job template as description
#         if obj.ai_response_payload and 'jobTemplate' in obj.ai_response_payload:
#             template = obj.ai_response_payload['jobTemplate']
#             # Return first 200 characters as description
#             # return template[:200] + "..." if len(template) > 200 else template
#             return template
#         return ""

#     def get_total_applicants(self, obj):
#         # You'll need to implement applicant tracking
#         # For now, return 0 or mock data
#         return 0


from django.utils.html import strip_tags
class JobTaskSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    job_description = serializers.SerializerMethodField()
    posted_on = serializers.DateTimeField(source="created_at", read_only=True)
    total_applicants = serializers.SerializerMethodField()

    class Meta:
        model = JobTask
        fields = ['id', 'job_title', 'job_description', 'posted_on', 'total_applicants', 'status']

    def get_job_title(self, obj):
        """
        WordPress se live title fetch karta hai
        """
        print(f"Getting title for task {obj.id}, status: {obj.status}, wp_page_url: {obj.wp_page_url}")
        
        # Only try WordPress if status is completed and URL exists
        if (obj.status == "completed" and 
            obj.wp_page_url and 
            hasattr(obj.user, 'wordpress_connection') and 
            obj.user.wordpress_connection):
            
            try:
                print(f"Trying WordPress fetch for: {obj.wp_page_url}")
                wp_data = fetch_wordpress_post_data(obj.user.wordpress_connection, obj.wp_page_url)
                if wp_data and wp_data.get('title'):
                    title = strip_tags(wp_data['title'])
                    print(f"WordPress title found: {title}")
                    return title.strip()
                else:
                    print("WordPress data not found or no title")
            except Exception as e:
                print(f"Failed to fetch WordPress title: {e}")
        
        # For failed tasks or when WordPress fails, use AI response data
        print("Trying AI response payload for title")
        if obj.ai_response_payload:
            # Handle both dict and string formats
            if isinstance(obj.ai_response_payload, dict):
                if 'title' in obj.ai_response_payload:
                    return obj.ai_response_payload['title']
                
                if 'jobTemplate' in obj.ai_response_payload:
                    template = obj.ai_response_payload['jobTemplate']
                    lines = template.split('\n')
                    for line in lines:
                        clean_line = line.strip()
                        if clean_line and not clean_line.startswith('<'):
                            return clean_line
            
            elif isinstance(obj.ai_response_payload, str):
                # If it's a string, try to extract first line
                lines = obj.ai_response_payload.split('\n')
                for line in lines:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith('<'):
                        return clean_line
        
        # Fallback to request payload
        print("Trying request payload for title")
        if obj.ai_request_payload and isinstance(obj.ai_request_payload, dict):
            company = obj.ai_request_payload.get('company_name', '')
            position = obj.ai_request_payload.get('position', 'Driver')
            return f"{company} - {position}"
        
        # Final fallback
        print("Using final fallback for title")
        return f"{obj.job_onboarding.company_name if obj.job_onboarding else 'Company'} - Driver Position"

    def get_job_description(self, obj):
        """
        WordPress se live description fetch karta hai
        """
        print(f"Getting description for task {obj.id}, status: {obj.status}")
        
        # Only try WordPress if status is completed and URL exists
        if (obj.status == "completed" and 
            obj.wp_page_url and 
            hasattr(obj.user, 'wordpress_connection') and 
            obj.user.wordpress_connection):
            
            try:
                wp_data = fetch_wordpress_post_data(obj.user.wordpress_connection, obj.wp_page_url)
                if wp_data:
                    description_text = wp_data.get('excerpt') or wp_data.get('content') or ''
                    if description_text:
                        clean_text = strip_tags(description_text)
                        clean_text = ' '.join(clean_text.split())
                        return clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
            except Exception as e:
                print(f"Failed to fetch WordPress description: {e}")
        
        # For failed tasks or when WordPress fails, use AI response data
        print("Trying AI response payload for description")
        if obj.ai_response_payload:
            if isinstance(obj.ai_response_payload, dict) and 'jobTemplate' in obj.ai_response_payload:
                template = obj.ai_response_payload['jobTemplate']
                clean_text = strip_tags(template)
                clean_text = ' '.join(clean_text.split())
                return clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
            
            elif isinstance(obj.ai_response_payload, str):
                clean_text = strip_tags(obj.ai_response_payload)
                clean_text = ' '.join(clean_text.split())
                return clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
        
        return "No description available"

    def get_total_applicants(self, obj):
        return 0
    




# serializers.py
from rest_framework import serializers
from django.utils.html import strip_tags
from .models import JobTemplate

class JobTemplateSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    job_description = serializers.SerializerMethodField()
    posted_on = serializers.DateTimeField(source="created_at", read_only=True)
    total_applicants = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="job_onboarding.company_name", read_only=True)

    class Meta:
        model = JobTemplate
        fields = [
            'id', 'job_title', 'job_description', 'posted_on', 
            'total_applicants', 'status', 'wp_page_url', 'company_name',
            'published_date'
        ]

    def get_job_title(self, obj):
        """Get job title from WordPress or AI response"""
        # Try WordPress first
        if obj.status == "completed" and obj.wp_page_url:
            try:
                wp_data = fetch_wordpress_post_data(obj.user.wordpress_connection, obj.wp_page_url)
                if wp_data and wp_data.get('title'):
                    return strip_tags(wp_data['title']).strip()
            except Exception:
                pass
        
        # Fallback to AI response
        if obj.ai_response_payload:
            if isinstance(obj.ai_response_payload, dict):
                if 'title' in obj.ai_response_payload:
                    return obj.ai_response_payload['title']
                
                if 'jobTemplate' in obj.ai_response_payload:
                    template = obj.ai_response_payload['jobTemplate']
                    lines = template.split('\n')
                    for line in lines:
                        clean_line = line.strip()
                        if clean_line and not clean_line.startswith('<'):
                            return clean_line
            
            elif isinstance(obj.ai_response_payload, str):
                lines = obj.ai_response_payload.split('\n')
                for line in lines:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith('<'):
                        return clean_line
        
        # Fallback to request payload
        if obj.ai_request_payload and isinstance(obj.ai_request_payload, dict):
            company = obj.ai_request_payload.get('company_name', '')
            position = obj.ai_request_payload.get('position', 'Driver')
            return f"{company} - {position}"
        
        # Final fallback
        return f"{obj.job_onboarding.company_name} - Driver Position"

    def get_job_description(self, obj):
        """Get job description from WordPress or AI response"""
        if obj.status == "completed" and obj.wp_page_url:
            try:
                wp_data = fetch_wordpress_post_data(obj.user.wordpress_connection, obj.wp_page_url)
                if wp_data:
                    description_text = wp_data.get('excerpt') or wp_data.get('content') or ''
                    if description_text:
                        clean_text = strip_tags(description_text)
                        clean_text = ' '.join(clean_text.split())
                        return clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
            except Exception:
                pass
        
        # Fallback to AI response
        if obj.ai_response_payload:
            if isinstance(obj.ai_response_payload, dict) and 'jobTemplate' in obj.ai_response_payload:
                template = obj.ai_response_payload['jobTemplate']
                clean_text = strip_tags(template)
                clean_text = ' '.join(clean_text.split())
                return clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
            
            elif isinstance(obj.ai_response_payload, str):
                clean_text = strip_tags(obj.ai_response_payload)
                clean_text = ' '.join(clean_text.split())
                return clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
        
        return "No description available"

    def get_total_applicants(self, obj):
        # You can implement applicant counting logic here
        return 0