from django.urls import path
from .views import *

urlpatterns = [
    path('create-subscription/', CreateSubscription.as_view(), name='create-subscription'),
    path('upgrade-subscription/', UpgradeSubscriptionAPIView.as_view(), name='upgrade-subscription'),
    path('get-subscriptions-details/',SubscriptionDetailsAPIView.as_view()),
    path('webhook/', stripe_webhook, name='stripe-webhook')
]
