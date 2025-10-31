# search_console/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class SearchConsoleToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credentials = models.JSONField()
    site_url = models.CharField(max_length=255, blank=True)


class GoogleAnalyticsToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expiry = models.DateTimeField()
    property_id = models.CharField(max_length=255, null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)



class GoogleBusinessToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credentials = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class BusinessProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=255)
    location_id = models.CharField(max_length=255)
    location_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'location_id']

class Review(models.Model):
    business_profile = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE)
    review_id = models.CharField(max_length=255, unique=True)
    reviewer_name = models.CharField(max_length=255)
    comment = models.TextField()
    star_rating = models.IntegerField()
    review_date = models.DateTimeField()
    has_response = models.BooleanField(default=False)
    response_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AIResponseLog(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    request_data = models.JSONField()
    response_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)