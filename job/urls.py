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

    # Jobber-specific endpoints
    path('crm/jobber/connections/<int:connection_id>/contacts/', JobberContactListAPIView.as_view(), name='jobber-contact-list'),
    path('crm/jobber/connections/<int:connection_id>/contacts/create/', JobberContactCreateAPIView.as_view(), name='jobber-contact-create'),
    path('crm/jobber/connections/<int:connection_id>/contacts/<str:contact_id>/', JobberContactUpdateAPIView.as_view(), name='jobber-contact-update'),
    path('crm/jobber/connections/<int:connection_id>/jobs/', JobberJobCreateAPIView.as_view(), name='jobber-job-create'),
    path('crm/jobber/connections/<int:connection_id>/jobs/<str:job_id>/close/', JobberJobCloseAPIView.as_view(), name='jobber-job-close'),

    # Zendesk-specific endpoints
    path('crm/zendesk/connections/<int:connection_id>/contacts/', ZendeskContactListAPIView.as_view(), name='zendesk-contact-list'),
    path('crm/zendesk/connections/<int:connection_id>/contacts/create/', ZendeskContactCreateAPIView.as_view(), name='zendesk-contact-create'),
    path('crm/zendesk/connections/<int:connection_id>/contacts/<str:contact_id>/', ZendeskContactUpdateAPIView.as_view(), name='zendesk-contact-update'),
    path('crm/zendesk/connections/<int:connection_id>/tickets/', ZendeskTicketCreateAPIView.as_view(), name='zendesk-ticket-create'),
    path('crm/zendesk/connections/<int:connection_id>/tickets/<str:ticket_id>/close/', ZendeskTicketCloseAPIView.as_view(), name='zendesk-ticket-close'),

    # SalesForce-specific endpoints
    path('crm/salesforce/connections/<int:connection_id>/contacts/', SalesForceContactListAPIView.as_view(), name='salesforce-contact-list'),
    path('crm/salesforce/connections/<int:connection_id>/contacts/create/', SalesForceContactCreateAPIView.as_view(), name='salesforce-contact-create'),
    path('crm/salesforce/connections/<int:connection_id>/contacts/<str:contact_id>/', SalesForceContactUpdateAPIView.as_view(), name='salesforce-contact-update'),
    path('crm/salesforce/connections/<int:connection_id>/opportunities/', SalesForceOpportunityCreateAPIView.as_view(), name='salesforce-opportunity-create'),
    path('crm/salesforce/connections/<int:connection_id>/opportunities/<str:opportunity_id>/close/', SalesForceOpportunityCloseAPIView.as_view(), name='salesforce-opportunity-close'),

    path('debug/zoho-token/<int:connection_id>/', DebugZohoTokenView.as_view(), name='debug-zoho-token'),
    
    path('feedback/form/<uuid:token>/', feedback_form_view, name='feedback-form'),
    path('api/feedback/form/<uuid:token>/submit/', submit_feedback_form, name='submit-feedback-form'),

    path('feedback/form-responses/', AllFeedbackFormResponsesAPIView.as_view(), name='all-feedback-form-responses'),
    path('feedback/form-responses/<int:response_id>/', FeedbackFormResponseByIdAPIView.as_view(), name='feedback-form-response-by-id'),


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
