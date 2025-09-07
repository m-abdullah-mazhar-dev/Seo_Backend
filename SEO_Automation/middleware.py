# core/middleware.py
import os
from django.conf import settings
from SEO_Automation.db_router import set_current_service

class ServiceTypeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        print(f"--------------------Host {host}")

        if host == settings.SEO_DOMAIN:
            service_type = "seo"
        elif host == settings.TRUCKING_DOMAIN:
            service_type = "trucking"
        else:
            service_type = "seo"  # default fallback

        set_current_service(service_type)
        request.service_type = service_type
        return self.get_response(request)
