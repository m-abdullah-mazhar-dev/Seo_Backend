from django.urls import path
from .views import *

urlpatterns = [
    path('create-subscription/', CreateSubscription.as_view(), name='create-subscription'),
    path('stripe/webhook/', stripe_webhook, name='stripe-webhook')
]
