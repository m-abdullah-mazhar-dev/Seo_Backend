# serializers.py

from rest_framework import serializers
from .models import *

class JobOnboardingFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOnboardingForm
        fields = '__all__'

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