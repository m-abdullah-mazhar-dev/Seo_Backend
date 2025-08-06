# search_console/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from django.contrib.auth.models import User
from g_matrix.google_service import get_flow, build_service
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
        user = request.user
        try:
            token = SearchConsoleToken.objects.get(user=user)
        except SearchConsoleToken.DoesNotExist:
            return Response({"error": "No token found"}, status=400)

        service = build_service(token.credentials)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=30)

        response = service.searchanalytics().query(
            siteUrl=token.site_url,
            body={
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'rowLimit': 5000,
            }
        ).execute()
        # onboarding = OnboardingForm.objects.get(user= user)
        keyword_map = {k.keyword.lower(): k for k in Keyword.objects.filter(service__onboarding_form__user = user)}
        print(keyword_map,"-------------------------")

        for row in response.get('rows', []):
            query = row['keys'][0].lower()
            if query in keyword_map:
                k = keyword_map[query]
                k.clicks = row.get('clicks', 0)
                k.impressions = row.get('impressions', 0)
                k.ctr = row.get('ctr', 0)
                k.average_position = row.get('position', 0)
                k.save()

        return Response({"message": "✅ Synced keyword metrics from Google Search Console."})
