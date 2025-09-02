from django.urls import path
from .views import * 

urlpatterns = [
    path('packages/create/', PackageCreateAPIView.as_view(), name='package-create'),
    path('packages/create/<int:pk>/', PackageCreateAPIView.as_view(), name='package-create'),

    path('onboarding/', OnBoardingFormAPIView.as_view(), name= "onboarding"),
    path('onboarding/<int:pk>/', OnBoardingFormAPIView.as_view()),
    path('connect_wp/', ConnectWordPressAPI.as_view()),
    path('connect_wp/job/', ConnectWordPressAPIJob.as_view()),
    path('verify_wp_connection/', VerifyWordPressConnectionAPI.as_view()),
    path('submit_service_page/', SubmitServicePageAPI.as_view()),

    path('my-service-areas/', MyServiceAreasView.as_view(), name='my-service-areas'),
    path('my-keywords/', MyKeywordsView.as_view(), name='my-keywords'),
    path('get_keyword_metrics/', get_keyword_metrics, name='get_keyword_metrics'),
    path('my-blogs/', MyBlogsView.as_view(), name='my-blogs'),
    path('my-blogs/<int:pk>/', MyBlogsView.as_view(), name='my-blog-detail'),
    path('edit-blog/<int:blog_id>/', BlogEditView.as_view(), name='edit-blog'),

    # path("stop/",StopAutomation.as_view()),
    # path("start/",StartAutomation.as_view()),
    path("start-stop/",AutomationToggleAPI.as_view()),

    path("user_details/", AdminClientListAPIView.as_view()),


    path("company_details/", CompanyDetailsAPIView.as_view()),

    path("user/setup-status/", UserSetupStatusAPI.as_view(), name="user-setup-status"),
]
