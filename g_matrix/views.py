# search_console/views.py

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from django.contrib.auth.models import User
from g_matrix.google_service import get_flow, build_service
from g_matrix.utils import sync_user_keywords
from .models import *
from seo_services.models import Keyword, OnboardingForm
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from rest_framework.permissions import IsAuthenticated
import requests
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes




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





import logging

logger = logging.getLogger(__name__)

# @login_required
def google_analytics_auth_start(request):
    logger.info("Started GA Auth")
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    scope = "https://www.googleapis.com/auth/analytics.readonly"
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    print(redirect_uri)
    auth_url = (
        f"{base_url}?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}&response_type=code&scope={scope}&access_type=offline&prompt=consent"
    )
    return redirect(auth_url)

import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from django.conf import settings

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_oauth2callback(request):


    accounts = []
    property_id = None
    account_name = "Unknown"

    # Debug: Log the start of the callback
    print("\n=== STARTING OAUTH2 CALLBACK ===")
    print(f"Incoming request params: {request.GET}")
    
    code = request.GET.get("code")
    if not code:
        print("ERROR: Missing authorization code")
        return JsonResponse({"error": "Missing authorization code"}, status=400)

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET

    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    print("\n=== TOKEN REQUEST ===")
    print(f"Making token request to: {token_url}")
    print(f"Token data: { {k: v for k, v in token_data.items() if k != 'client_secret'} }")

    token_response = requests.post(token_url, data=token_data)
    
    print("\n=== TOKEN RESPONSE ===")
    print(f"Status code: {token_response.status_code}")
    print(f"Response content: {token_response.text}")

    if token_response.status_code != 200:
        return JsonResponse({
            "error": "Failed to exchange code",
            "status_code": token_response.status_code,
            "response": token_response.text,
        })

    tokens = token_response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    print("\n=== TOKENS OBTAINED ===")
    print(f"Access token: {'exists' if access_token else 'missing'}")
    print(f"Refresh token: {'exists' if refresh_token else 'missing'}")
    print(f"Token expiry: {tokens.get('expires_in', 'unknown')} seconds")

    if not access_token:
        return JsonResponse({"error": "Access token missing"}, status=400)

    # Create credentials object
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/analytics.edit"
        ],
    )

    try:
        print("\n=== BUILDING SERVICES ===")
        # Try both v1beta and v1alpha versions
        try:
            admin_service = build("analyticsadmin", "v1beta", credentials=creds)
            print("Using analyticsadmin v1beta")
        except:
            admin_service = build("analyticsadmin", "v1alpha", credentials=creds)
            print("Falling back to analyticsadmin v1alpha")

        # First try to get account summaries
        try:
            print("\n=== TRYING ACCOUNT SUMMARIES ===")
            account_summaries = admin_service.accountSummaries().list().execute()
            summaries = account_summaries.get('accountSummaries', [])
            
            if summaries:
                account_name = summaries[0].get('displayName', "Unknown")
                properties = summaries[0].get('propertySummaries', [])
                if properties:
                    property_name = properties[0]["property"]
                    property_id = property_name.split("/")[-1]
                    print(f"Found property via summaries: {property_id}")
                    # Get accounts list for saving
                    accounts = admin_service.accounts().list().execute().get('accounts', [])
        except Exception as e:
            print(f"Couldn't get account summaries: {str(e)}")

        # If we still don't have a property ID, try the direct approach
        if not property_id:
            print("\n=== TRYING DIRECT ACCOUNT ACCESS ===")
            try:
                accounts_response = admin_service.accounts().list().execute()
                accounts = accounts_response.get("accounts", [])
                
                if accounts:
                    account_name = accounts[0].get("displayName", "Unknown")
                    account_id = accounts[0]["name"].split("/")[-1]
                    print(f"Account ID: {account_id}")
                    
                    # Try to list properties
                    properties = admin_service.properties().list(
                        filter=f"parent:accounts/{account_id}"
                    ).execute().get('properties', [])
                    
                    if properties:
                        property_id = properties[0]["name"].split("/")[-1]
                        print(f"Found property via direct listing: {property_id}")
            except Exception as e:
                print(f"Couldn't list properties directly: {str(e)}")

        # If we still don't have a property ID, try the Data API
        if not property_id:
            print("\n=== TRYING DATA API ===")
            try:
                data_service = build("analyticsdata", "v1beta", credentials=creds)
                response = data_service.properties().list().execute()
                properties = response.get('properties', [])
                if properties:
                    property_id = properties[0]["name"].split("/")[-1]
                    print(f"Found property via Data API: {property_id}")
            except Exception as e:
                print(f"Couldn't get properties via Data API: {str(e)}")

        # If we still don't have a property ID, fail
        if not property_id:
            return JsonResponse({
                "error": "Could not find any GA4 properties",
                "debug": {
                    "available_scopes": creds.scopes,
                    "token_info": {
                        "expires_in": tokens.get("expires_in"),
                        "scopes": tokens.get("scope", "").split()
                    }
                }
            }, status=400)

        # Save everything
        GoogleAnalyticsToken.objects.update_or_create(
            user=request.user,
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": timezone.now() + timedelta(seconds=int(tokens.get("expires_in", 3600))),
                "property_id": property_id,
                "account_name": account_name,
            }
        )

        return JsonResponse({
            "success": True,
            "property_id": property_id,
            "account": account_name,
        })

    except Exception as e:
        print(f"\nFINAL ERROR: {str(e)}")
        return JsonResponse({
            "error": "Failed to complete Google Analytics setup",
            "details": str(e),
            "type": type(e).__name__,
            "suggestion": "Ensure the Google Analytics Admin API and Data API are enabled in your Google Cloud project"

        }, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_analytics_data(request):
    try:
        token = GoogleAnalyticsToken.objects.get(user=request.user)
    except GoogleAnalyticsToken.DoesNotExist:
        return Response({"error": "Google Analytics not connected."}, status=400)

    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json"
    }

    if not token.property_id:
        return Response({"error": "Google Analytics property not set."}, status=400)

    body = {
        "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
        "metrics": [
            {"name": "totalUsers"},  # Changed from 'users' to 'totalUsers'
            {"name": "sessions"},
            {"name": "bounceRate"},
            {"name": "averageSessionDuration"},
            {"name": "newUsers"},
            {"name": "screenPageViews"}
        ],
        "dimensions": [{"name": "pageTitle"}]
    }

    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{token.property_id}:runReport"
    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 401:
        return Response({"error": "Unauthorized. Try reconnecting Google Analytics."}, status=401)
    elif response.status_code != 200:
        return Response({
            "error": "Google Analytics API error",
            "details": response.json()
        }, status=response.status_code)

    return Response(response.json())