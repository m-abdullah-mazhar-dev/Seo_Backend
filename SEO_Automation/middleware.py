# core/middleware.py
import os
from django.conf import settings
from SEO_Automation.db_router import set_current_service
import logging
logger = logging.getLogger(__name__)

class ServiceTypeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        referer = request.META.get("HTTP_REFERER", "")
        origin = request.META.get("HTTP_ORIGIN", "")

        logger.info(f"Origin: {origin}")
        logger.info(f"Referer: {referer}")
        logger.info(f"--------------------Host {host}")

        if settings.SEO_DOMAIN in referer or settings.SEO_DOMAIN in origin:
            service_type = "seo"
        elif settings.TRUCKING_DOMAIN in referer or settings.TRUCKING_DOMAIN in origin:
            service_type = "trucking"
        else:
            service_type = "seo"  # default fallback

        set_current_service(service_type)
        request.service_type = service_type
        return self.get_response(request)

