"""
URL configuration for SEO_Automation project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import *


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include("authentication.urls") ),
    path('payment/', include("payment.urls") ),
    path('seo/', include("seo_services.urls") ),
    path('job/', include("job.urls") ),
    path('stripe/', include("payment.urls") ),
    # Auth routes
    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
     # ✅ Add this for social login
    path('dj-rest-auth/google/', GoogleLoginJWTOny.as_view(), name='google_login_jwt'),

    # Required for social login callback (even if unused directly)
    path('accounts/', include('allauth.urls')),


    path('search-console/', include('g_matrix.urls')),
    path('google_analytics/', include('g_matrix.urls')),
    path('google-business/', include('g_matrix.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
