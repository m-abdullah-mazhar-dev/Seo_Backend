# search_console/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from django.contrib.auth.models import User
from g_matrix.google_service import get_flow, build_service
from g_matrix.utils import sync_user_keywords
from .models import SearchConsoleToken
from seo_services.models import Keyword, OnboardingForm
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from rest_framework.permissions import IsAuthenticated


class AuthStartView(APIView):
    def get(self, request):
        flow = get_flow()
        auth_url, _ = flow.authorization_url(prompt='consent')
        return redirect(auth_url)


class AuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        flow = get_flow()
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials

        # Call Search Console API to get the verified site
        service = build('searchconsole', 'v1', credentials=creds)
        site_list = service.sites().list().execute()
        user_site_url = None
        for site in site_list.get("siteEntry", []):
            if site.get("permissionLevel") == "siteOwner":
                user_site_url = site.get("siteUrl")
                break

        if not user_site_url:
            return Response({"error": "No site with owner permissions found."}, status=400)

        user = request.user  # Replace this with your user logic (e.g., session or token auth)
        print(f"{user} --------------------")

        SearchConsoleToken.objects.update_or_create(
            user=user,
            defaults={
                "site_url": user_site_url,
                "credentials": {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes
                }
            }
        )

        return Response({"message": "✅ Auth successful. Token and site URL saved."})

class SyncKeywordMetricsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        result = sync_user_keywords(request.user)
        return Response(result)
