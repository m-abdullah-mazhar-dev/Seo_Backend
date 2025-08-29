# serializers.py

from rest_framework import serializers
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
    redirect_uri = serializers.URLField()

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


class JobTaskSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    job_description = serializers.SerializerMethodField()
    posted_on = serializers.DateTimeField(source="created_at", read_only=True)
    total_applicants = serializers.SerializerMethodField()  # You'll need to implement this

    class Meta:
        model = JobTask
        fields = ['id', 'job_title', 'job_description', 'posted_on', 'total_applicants', 'status']

    def get_job_title(self, obj):
        # Extract job title from the AI response payload
        if obj.ai_response_payload and 'jobTemplate' in obj.ai_response_payload:
            # You might want to parse the template to extract a proper title
            return f"{obj.job_onboarding.company_name} - Driver Position"
        return "Job Position"

    def get_job_description(self, obj):
        # Return the first part of the job template as description
        if obj.ai_response_payload and 'jobTemplate' in obj.ai_response_payload:
            template = obj.ai_response_payload['jobTemplate']
            # Return first 200 characters as description
            # return template[:200] + "..." if len(template) > 200 else template
            return template
        return ""

    def get_total_applicants(self, obj):
        # You'll need to implement applicant tracking
        # For now, return 0 or mock data
        return 0