from django.urls import path
from .views import *

urlpatterns = [
    path('job_onboarding/',CreateJobOnboardingFormAPIView.as_view() , name = "job_onboarding"),
    path('job_onboarding/<int:pk>/',CreateJobOnboardingFormAPIView.as_view() , name = "job_onboarding"),
    path('submit_job_page/',SubmitJobPageAPI.as_view() , name = "submit_job_url"),
    path('job-closed/',JobClosedAPIView.as_view() , name = "job-close"),
    path("feedback/<uuid:token>/<str:answer>/", FeedbackAPI.as_view(), name="api-feedback"),

]
