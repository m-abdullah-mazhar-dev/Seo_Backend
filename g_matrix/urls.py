# search_console/urls.py

from django.urls import path
from g_matrix.views import *
from django.views.generic import TemplateView

urlpatterns = [
    path('auth/start/', SearchAuthStartView.as_view(), name='search_console_auth_start'),
    path('oauth2callback/', SearchAuthCallbackView.as_view(), name='search_console_auth_callback'),
    path('sync/', SyncKeywordMetricsView.as_view(), name='search_console_sync'),
    path('service_page_clicks/', ServicePageMetricsView.as_view(), name='search_console_service_page'),


    path('analytics/auth/start/', google_analytics_auth_start, name='ga_auth_start'),
    path('analytics/oauth2callback/', analytics_oauth2callback, name='ga_auth_callback'),
    path('analytics/fetch-data/', fetch_analytics_data, name='ga_fetch_data'),

    path('profile/auth/start/', AuthStartView.as_view(), name='gbp_auth_start'),
    path('profile/auth/callback/', AuthCallbackView.as_view(), name='gbp_auth_callback'),
    path('profile/accounts/', ListBusinessesView.as_view(), name='gbp_accounts'),

    path("test-ga-callback/", TemplateView.as_view(template_name="g_metrix/test_ga_callback.html"))
]
