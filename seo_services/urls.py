from django.urls import path
from .views import * 

urlpatterns = [
    path('packages/create/', PackageCreateAPIView.as_view(), name='package-create'),
    path('packages/create/<int:pk>/', PackageCreateAPIView.as_view(), name='package-create'),

    path('onboarding/', OnBoardingFormAPIView.as_view(), name= "onboarding"),
    path('onboarding/<int:pk>/', OnBoardingFormAPIView.as_view()),
    path('connect_wp/', ConnectWordPressAPI.as_view()),
    path('verify_wp_connection/', VerifyWordPressConnectionAPI.as_view()),
    path('submit_service_page/', SubmitServicePageAPI.as_view()),

    path('my-service-areas/', MyServiceAreasView.as_view(), name='my-service-areas'),
    path('my-keywords/', MyKeywordsView.as_view(), name='my-keywords'),
    path('my-blogs/', MyBlogsView.as_view(), name='my-blogs'),


]
