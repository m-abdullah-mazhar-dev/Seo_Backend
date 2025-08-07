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

