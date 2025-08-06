# search_console/urls.py

from django.urls import path
from g_matrix.views import AuthStartView, AuthCallbackView, SyncKeywordMetricsView

urlpatterns = [
    path('auth/start/', AuthStartView.as_view(), name='search_console_auth_start'),
    path('oauth2callback/', AuthCallbackView.as_view(), name='search_console_auth_callback'),
    path('sync/', SyncKeywordMetricsView.as_view(), name='search_console_sync'),
]
