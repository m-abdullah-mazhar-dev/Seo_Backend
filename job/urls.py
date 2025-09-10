from django.urls import path
from .views import *

urlpatterns = [
    path('job_onboarding/',CreateJobOnboardingFormAPIView.as_view() , name = "job_onboarding"),
    path('job_onboarding/<int:pk>/',CreateJobOnboardingFormAPIView.as_view() , name = "job_onboarding"),
    path('submit_job_page/',SubmitJobPageAPI.as_view() , name = "submit_job_url"),
    # path('job-closed/',JobClosedAPIView.as_view() , name = "job-close"),
    # path("feedback/<uuid:token>/<str:answer>/", FeedbackAPI.as_view(), name="api-feedback"),



    # CRM integration endpoints
    path('crm/types/',  CRMTypeListAPIView.as_view(), name='crm-types'),
    path('crm/connections/',  CRMConnectionListAPIView.as_view(), name='crm-connections'),
    path('crm/connections/create/',  CRMConnectionCreateAPIView.as_view(), name='crm-connection-create'),
    path('crm/oauth/init/',  OAuthInitAPIView.as_view(), name='crm-oauth-init'),
    path('crm/oauth/callback/',  OAuthCallbackAPIView.as_view(), name='crm-oauth-callback'),
    path('crm/connections/<int:pk>/',  CRMConnectionDetailAPIView.as_view(), name='crm-connection-detail'),
    path('crm/connections/<int:connection_id>/jobs/',  CRMJobCreateAPIView.as_view(), name='crm-job-create'),
    path('crm/connections/<int:connection_id>/jobs/<str:job_id>/close/',  CRMJobCloseAPIView.as_view(), name='crm-job-close'),

    path('debug/zoho-token/<int:connection_id>/', DebugZohoTokenView.as_view(), name='debug-zoho-token'),
    
    # Webhook and feedback endpoints
    path('webhook/job-closed/<uuid:secret_token>/',  CRMWebhookAPIView.as_view(), name='crm-webhook'),
    path('feedback/<uuid:token>/<str:answer>/',  FeedbackAPI.as_view(), name='api-feedback'),

    # JObs get api 
    path('my-job-posts/', MyJobPostsView.as_view(), name='my-job-posts'),
    path('my-job-posts/<int:pk>/', MyJobPostsView.as_view(), name='my-job-posts'),
    path('my-job-blogs/', MyJobBlogsView.as_view(), name='my-job-blogs'),

    path('total-jobs/',JobPostCountView.as_view()),
    path("all_stats/", JobStatsAPIView.as_view()),



    path('jobs/sync/', JobContentMetricsView.as_view(), name='sync-job-metrics'),
    path('jobs/keywords/sync/', SyncJobKeywordsView.as_view(), name='sync-job-keywords'),
    path('jobs/analytics/sync/', JobContentAnalyticsView.as_view(), name='sync-job-analytics'),
    path('jobs/performance/', JobPerformanceDashboardView.as_view(), name='job-performance-dashboard'),
    

]
