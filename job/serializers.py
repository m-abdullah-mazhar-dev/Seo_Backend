# serializers.py

from rest_framework import serializers
from .models import JobOnboardingForm

class JobOnboardingFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOnboardingForm
        fields = '__all__'
