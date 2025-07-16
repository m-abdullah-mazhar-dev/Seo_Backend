from rest_framework import serializers
from .models import UserSubscription
from seo_services.models import Package

class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ['id', 'name', 'stripe_price_id']  # include other fields if needed

class UserSubscriptionSerializer(serializers.ModelSerializer):
    package = PackageSerializer()  # nested serializer

    class Meta:
        model = UserSubscription
        fields = ['package', 'stripe_customer_id', 'stripe_subscription_id', 'status', 'current_period_end']
