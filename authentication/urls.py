from django.urls import path
from .views import *

urlpatterns = [
    path('register/', RegisterApi.as_view(), name = "register"),      # User-related APIs
    path('login/', UserLoginApi.as_view(), name = "login"),      # User-related APIs
    path('change-password/', ChangePasswordApi.as_view()),
]
