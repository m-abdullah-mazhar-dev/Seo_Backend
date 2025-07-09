from django.db import models
from django.contrib.auth import get_user_model
from seo_services.models import Package
User = get_user_model()

# Create your models here.
class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('past_due', 'Past Due'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True)
    stripe_customer_id = models.CharField(max_length=200)
    stripe_subscription_id = models.CharField(max_length=200)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='incomplete')
    current_period_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.status}"
