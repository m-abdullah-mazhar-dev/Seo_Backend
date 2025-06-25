from django.urls import path
from .views import * 

urlpatterns = [
    path('onboarding/', OnBoardingFormAPIView.as_view(), name= "onboarding"),
    path('onboarding/<int:pk>/', OnBoardingFormAPIView.as_view()),
    path('connect_wp/', ConnectWordPressAPI.as_view()),
    path('verify_wp_connection/', VerifyWordPressConnectionAPI.as_view()),
    path('submit_service_page/', SubmitServicePageAPI.as_view()),


]
