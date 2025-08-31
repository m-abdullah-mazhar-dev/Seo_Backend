# search_console/views.py

from urllib.parse import urlparse
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from django.contrib.auth.models import User
from g_matrix.google_service import get_flow_search, build_service
from g_matrix.utils import sync_user_keywords
from .models import *
from seo_services.models import Keyword, OnboardingForm, SEOTask
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from rest_framework.permissions import IsAuthenticated
import requests
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
import os
from google_auth_oauthlib.flow import Flow
from django.db.models import Q






class SearchAuthStartView(APIView):
    def get(self, request):
        flow = get_flow_search()
        auth_url, _ = flow.authorization_url(prompt='consent')
        return redirect(auth_url)


class SearchAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        code = request.data.get("code") or request.query_params.get("code")
        if not code:
            return Response({"error": "Missing code"}, status=400)
        flow = get_flow_search()
        # flow.fetch_token(authorization_response=request.build_absolute_uri())
        flow.fetch_token(code=code)
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

class ServicePageMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            token = SearchConsoleToken.objects.get(user=user)
        except SearchConsoleToken.DoesNotExist:
            return Response({"error": "Search Console not connected"}, status=400)

        tasks = SEOTask.objects.filter(
            user=user,
            wp_page_url__isnull=False
        ).exclude(wp_page_url='')

        if not tasks.exists():
            return Response({"message": "No service pages with URLs found"}, status=200)

        service = build_service(token.credentials)
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=30)

        # Extract domain from site_url (handles both domain and URL-prefix properties)
        if token.site_url.startswith('sc-domain:'):
            # For domain properties like 'sc-domain:example.com'
            domain = token.site_url.replace('sc-domain:', 'https://')
        else:
            # For URL-prefix properties like 'https://example.com/'
            domain = token.site_url.rstrip('/')

        # Build full URL expressions
        page_expressions = []
        for task in tasks:
            if task.wp_page_url:
                parsed = urlparse(task.wp_page_url)
                if parsed.netloc:  # If URL already has domain
                    page_expressions.append(task.wp_page_url)
                else:  # If just path, prepend domain
                    page_expressions.append(f"{domain}{parsed.path}")

        # Remove duplicates
        page_expressions = list(set(page_expressions))
        print(f"Querying expressions: {page_expressions}")

        try:
            response = service.searchanalytics().query(
                siteUrl=token.site_url,
                body={
                    'startDate': start_date.strftime('%Y-%m-%d'),
                    'endDate': end_date.strftime('%Y-%m-%d'),
                    'dimensions': ['page'],
                    'dimensionFilterGroups': [{
                        'filters': [{
                            'dimension': 'page',
                            'operator': 'equals',
                            'expression': expr
                        } for expr in page_expressions]
                    }]
                }
            ).execute()

            updated_tasks = []
            if 'rows' in response:
                for row in response.get('rows', []):
                    page_url = row['keys'][0]  # Full URL returned
                    path = urlparse(page_url).path
                    
                    # Match tasks by either full URL or path
                    matching_tasks = tasks.filter(
                        Q(wp_page_url__icontains=page_url) | 
                        Q(wp_page_url__endswith=path)
                    )
                    
                    for task in matching_tasks:
                        task.clicks = row.get('clicks', 0)
                        task.impressions = row.get('impressions', 0)
                        task.last_metrics_update = timezone.now()
                        task.save()
                        updated_tasks.append({
                            'task_id': task.id,
                            'page_url': task.wp_page_url,
                            'clicks': task.clicks,
                            'impressions': task.impressions
                        })

            return Response({
                'updated_count': len(updated_tasks),
                'tasks': updated_tasks,
                'queried_expressions': page_expressions,
                'found_rows': len(response.get('rows', []))
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)


import logging

logger = logging.getLogger(__name__)

# @login_required
def google_analytics_auth_start(request):
    logger.info("Started GA Auth")
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    scope = "https://www.googleapis.com/auth/analytics.readonly"
    redirect_uri = settings.GOOGLE_ANALYTICS_REDIRECT_URI
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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analytics_oauth2callback(request):

    accounts = []
    property_id = None
    account_name = "Unknown"

    # Debug: Log the start of the callback
    print("\n=== STARTING OAUTH2 CALLBACK ===")
    print(f"Incoming request params: {request.GET}")
    
    code = request.data.get("code")
    if not code:
        print("ERROR: Missing authorization code")
        return JsonResponse({"error": "Missing authorization code"}, status=400)

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = settings.GOOGLE_ANALYTICS_REDIRECT_URI
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
    
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def fetch_analytics_data(request):
#     try:
#         token = GoogleAnalyticsToken.objects.get(user=request.user)
#     except GoogleAnalyticsToken.DoesNotExist:
#         return Response({"error": "Google Analytics not connected."}, status=400)

#     headers = {
#         "Authorization": f"Bearer {token.access_token}",
#         "Content-Type": "application/json"
#     }

#     if not token.property_id:
#         return Response({"error": "Google Analytics property not set."}, status=400)

#     body = {
#         "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
#         "metrics": [
#             {"name": "totalUsers"},  # Changed from 'users' to 'totalUsers'
#             {"name": "sessions"},
#             {"name": "bounceRate"},
#             {"name": "averageSessionDuration"},
#             {"name": "newUsers"},
#             {"name": "screenPageViews"}
#         ],
#         "dimensions": [{"name": "pageTitle"}]
#     }

#     url = f"https://analyticsdata.googleapis.com/v1beta/properties/{token.property_id}:runReport"
#     response = requests.post(url, headers=headers, json=body)

#     if response.status_code == 401:
#         return Response({"error": "Unauthorized. Try reconnecting Google Analytics."}, status=401)
#     elif response.status_code != 200:
#         return Response({
#             "error": "Google Analytics API error",
#             "details": response.json()
#         }, status=response.status_code)

#     return Response(response.json())
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def fetch_analytics_data(request):
#     try:
#         token = GoogleAnalyticsToken.objects.get(user=request.user)
#     except GoogleAnalyticsToken.DoesNotExist:
#         return Response({"error": "Google Analytics not connected."}, status=400)

#     if not token.property_id:
#         return Response({"error": "Google Analytics property not set."}, status=400)

#     headers = {
#         "Authorization": f"Bearer {token.access_token}",
#         "Content-Type": "application/json"
#     }

#     # ==============================
#     # 1) HISTORICAL (last 30 days)
#     # ==============================
#     historical_body = {
#         "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
#         "metrics": [
#             {"name": "totalUsers"},
#             {"name": "newUsers"},
#             {"name": "sessions"},
#             {"name": "engagedSessions"},
#             {"name": "engagementRate"},
#             {"name": "averageSessionDuration"},
#             {"name": "bounceRate"},
#             {"name": "screenPageViews"}
#         ],
#         "dimensions": [
#             {"name": "pageTitle"},
#             {"name": "pagePath"},
#             {"name": "sessionDefaultChannelGrouping"},
#             {"name": "country"}
#         ]
#     }

#     historical_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{token.property_id}:runReport"
#     hist_resp = requests.post(historical_url, headers=headers, json=historical_body)
#     if hist_resp.status_code != 200:
#         return Response({"error": "Historical API error", "details": hist_resp.json()}, status=hist_resp.status_code)

#     hist_data = hist_resp.json().get("rows", [])

#     # Aggregate totals
#     total_users = new_users = sessions = engaged_sessions = page_views = 0
#     total_duration = total_bounce = 0

#     page_stats = {}
#     country_stats = {}
#     channel_stats = {}

#     for row in hist_data:
#         dims = row.get("dimensionValues", [])
#         mets = row.get("metricValues", [])

#         try:
#             page_title = dims[0]["value"]
#             page_path = dims[1]["value"]
#             channel = dims[2]["value"]
#             country = dims[3]["value"]

#             users = int(mets[0]["value"])
#             new_u = int(mets[1]["value"])
#             sess = int(mets[2]["value"])
#             engaged = int(mets[3]["value"])
#             engagement_rate = float(mets[4]["value"])
#             duration = float(mets[5]["value"])
#             bounce = float(mets[6]["value"])
#             views = int(mets[7]["value"])

#             # Aggregate totals
#             total_users += users
#             new_users += new_u
#             sessions += sess
#             engaged_sessions += engaged
#             total_duration += duration * sess
#             total_bounce += bounce * sess
#             page_views += views

#             # Per-page aggregation
#             if page_path not in page_stats:
#                 page_stats[page_path] = {"title": page_title, "views": 0, "bounce_sum": 0, "sessions": 0}
#             page_stats[page_path]["views"] += views
#             page_stats[page_path]["bounce_sum"] += bounce * sess
#             page_stats[page_path]["sessions"] += sess

#             # Per-country aggregation
#             country_stats[country] = country_stats.get(country, 0) + users

#             # Per-channel aggregation
#             channel_stats[channel] = channel_stats.get(channel, 0) + users

#         except (IndexError, ValueError):
#             continue

#     avg_session_duration_minutes = round((total_duration / sessions) / 60, 2) if sessions else 0
#     bounce_rate = round((total_bounce / sessions), 2) if sessions else 0

#     top_pages = sorted(
#         [{"page_title": v["title"], "page_path": k, "page_views": v["views"],
#           "bounce_rate": round(v["bounce_sum"] / v["sessions"], 2) if v["sessions"] else 0}
#          for k, v in page_stats.items()],
#         key=lambda x: x["page_views"], reverse=True
#     )[:5]

#     top_countries = sorted(
#         [{"country": k, "users": v} for k, v in country_stats.items()],
#         key=lambda x: x["users"], reverse=True
#     )[:5]

#     traffic_channels = sorted(
#         [{"channel": k, "users": v} for k, v in channel_stats.items()],
#         key=lambda x: x["users"], reverse=True
#     )

#     # ==============================
#     # 2) REAL-TIME
#     # ==============================
#     realtime_body = {
#         "metrics": [{"name": "activeUsers"}],
#         "dimensions": [{"name": "unifiedScreenName"}, {"name": "country"}]
#     }
#     realtime_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{token.property_id}:runRealtimeReport"
#     real_resp = requests.post(realtime_url, headers=headers, json=realtime_body)
#     if real_resp.status_code != 200:
#         return Response({"error": "Real-time API error", "details": real_resp.json()}, status=real_resp.status_code)

#     realtime_rows = real_resp.json().get("rows", [])
#     realtime_total = 0
#     realtime_pages = {}
#     realtime_countries = {}

#     for row in realtime_rows:
#         dims = row.get("dimensionValues", [])
#         mets = row.get("metricValues", [])

#         try:
#             page = dims[0]["value"]
#             country = dims[1]["value"]
#             active = int(mets[0]["value"])

#             realtime_total += active
#             realtime_pages[page] = realtime_pages.get(page, 0) + active
#             realtime_countries[country] = realtime_countries.get(country, 0) + active
#         except (IndexError, ValueError):
#             continue

#     return Response({
#         "summary": {
#             "total_users": total_users,
#             "new_users": new_users,
#             "sessions": sessions,
#             "bounce_rate": bounce_rate,
#             "avg_session_duration_minutes": avg_session_duration_minutes,
#             "page_views": page_views
#         },
#         "top_pages": top_pages,
#         "top_countries": top_countries,
#         "traffic_channels": traffic_channels,
#         "realtime": {
#             "active_users": realtime_total,
#             "top_pages": sorted(
#                 [{"page": k, "active_users": v} for k, v in realtime_pages.items()],
#                 key=lambda x: x["active_users"], reverse=True
#             ),
#             "countries": sorted(
#                 [{"country": k, "active_users": v} for k, v in realtime_countries.items()],
#                 key=lambda x: x["active_users"], reverse=True
#             )
#         }
#     })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_analytics_data(request):
    try:
        token = GoogleAnalyticsToken.objects.get(user=request.user)
    except GoogleAnalyticsToken.DoesNotExist:
        return Response({"error": "Google Analytics not connected."}, status=400)

    if not token.property_id:
        return Response({"error": "Google Analytics property not set."}, status=400)

    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json"
    }

    # ==============================
    # 1) HISTORICAL (last 30 days)
    # ==============================
    historical_body = {
        "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
        "metrics": [
            {"name": "totalUsers"},
            {"name": "newUsers"},
            {"name": "sessions"},
            {"name": "engagedSessions"},
            {"name": "engagementRate"},
            {"name": "averageSessionDuration"},
            {"name": "bounceRate"},
            {"name": "screenPageViews"},
            {"name": "userEngagementDuration"}  # avg time on page
        ],
        "dimensions": [
            {"name": "pageTitle"},
            {"name": "pagePath"},
            {"name": "sessionDefaultChannelGrouping"},
            {"name": "country"},
            {"name": "date"},
            {"name": "deviceCategory"}
        ]
    }

    historical_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{token.property_id}:runReport"
    hist_resp = requests.post(historical_url, headers=headers, json=historical_body)
    if hist_resp.status_code != 200:
        return Response({"error": "Historical API error", "details": hist_resp.json()}, status=hist_resp.status_code)

    hist_data = hist_resp.json().get("rows", [])

    # Aggregators
    total_users = new_users = sessions = page_views = 0
    total_duration = total_bounce = 0

    page_stats = {}
    country_stats = {}
    channel_stats = {}
    device_stats = {}
    trend_stats = {}  # date-wise

    for row in hist_data:
        dims = row.get("dimensionValues", [])
        mets = row.get("metricValues", [])

        try:
            page_title = dims[0]["value"]
            page_path = dims[1]["value"]
            channel = dims[2]["value"]
            country = dims[3]["value"]
            date_str = dims[4]["value"]
            device = dims[5]["value"]

            users = int(mets[0]["value"])
            new_u = int(mets[1]["value"])
            sess = int(mets[2]["value"])
            duration = float(mets[5]["value"])
            bounce = float(mets[6]["value"])
            views = int(mets[7]["value"])
            engagement_time = float(mets[8]["value"])

            # Totals
            total_users += users
            new_users += new_u
            sessions += sess
            total_duration += duration * sess
            total_bounce += bounce * sess
            page_views += views

            # Per-page
            if page_path not in page_stats:
                page_stats[page_path] = {"title": page_title, "views": 0, "engagement_time": 0, "sessions": 0,"bounce_sum": 0}
            page_stats[page_path]["views"] += views
            page_stats[page_path]["engagement_time"] += engagement_time
            page_stats[page_path]["sessions"] += sess
            page_stats[page_path]["bounce_sum"] += bounce * sess

            # Per-country
            country_stats[country] = country_stats.get(country, 0) + users

            # Per-channel
            channel_stats[channel] = channel_stats.get(channel, 0) + users

            # Per-device
            device_stats[device] = device_stats.get(device, 0) + users

            # Trend (date-wise)
            if date_str not in trend_stats:
                trend_stats[date_str] = {"users": 0, "views": 0}
            trend_stats[date_str]["users"] += users
            trend_stats[date_str]["views"] += views

        except (IndexError, ValueError):
            continue

    avg_session_duration_minutes = round((total_duration / sessions) / 60, 2) if sessions else 0
    bounce_rate = round((total_bounce / sessions), 2) if sessions else 0

    # Top pages (with avg time on page)
    top_pages = sorted(
        [
            {
                "page_title": v["title"],
                "page_path": k,
                "page_views": v["views"],
                "avg_time_on_page": round((v["engagement_time"] / v["sessions"]) if v["sessions"] else 0, 2),
                "bounce_rate": round((v["bounce_sum"] / v["sessions"]), 2) if v["sessions"] else 0
            }
            for k, v in page_stats.items()
        ],
        key=lambda x: x["page_views"], reverse=True
    )[:5]

    # Countries
    top_countries = sorted(
        [{"country": k, "users": v} for k, v in country_stats.items()],
        key=lambda x: x["users"], reverse=True
    )[:5]

    # Traffic channels with %
    channel_total = sum(channel_stats.values()) or 1
    traffic_channels = sorted(
        [{"channel": k, "users": v, "percent": round((v / channel_total) * 100, 2)} for k, v in channel_stats.items()],
        key=lambda x: x["users"], reverse=True
    )

    # Devices
    device_breakdown = [
        {"device": k, "users": v, "percent": round((v / total_users) * 100, 2) if total_users else 0}
        for k, v in device_stats.items()
    ]

    # Trends (convert dict to sorted list)
    traffic_trends = sorted(
        [{"date": k, "users": v["users"], "page_views": v["views"]} for k, v in trend_stats.items()],
        key=lambda x: x["date"]
    )

    # ==============================
    # 2) REAL-TIME
    # ==============================
    realtime_body = {
        "metrics": [{"name": "activeUsers"}],
        "dimensions": [{"name": "unifiedScreenName"}, {"name": "country"}]
    }
    realtime_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{token.property_id}:runRealtimeReport"
    real_resp = requests.post(realtime_url, headers=headers, json=realtime_body)
    if real_resp.status_code != 200:
        return Response({"error": "Real-time API error", "details": real_resp.json()}, status=real_resp.status_code)

    realtime_rows = real_resp.json().get("rows", [])
    realtime_total = 0
    realtime_pages = {}
    realtime_countries = {}

    for row in realtime_rows:
        dims = row.get("dimensionValues", [])
        mets = row.get("metricValues", [])

        try:
            page = dims[0]["value"]
            country = dims[1]["value"]
            active = int(mets[0]["value"])

            realtime_total += active
            realtime_pages[page] = realtime_pages.get(page, 0) + active
            realtime_countries[country] = realtime_countries.get(country, 0) + active
        except (IndexError, ValueError):
            continue

    return Response({
        "summary": {
            "total_users": total_users,
            "new_users": new_users,
            "sessions": sessions,
            "bounce_rate": bounce_rate,
            "avg_session_duration_minutes": avg_session_duration_minutes,
            "page_views": page_views
        },
        "traffic_trends": traffic_trends,  # ✅ for graph
        "traffic_channels": traffic_channels,  # ✅ with %
        "device_breakdown": device_breakdown,  # ✅ devices
        "top_pages": top_pages,  # ✅ with avg time
        "top_countries": top_countries,
        "realtime": {
            "active_users": realtime_total,
            "top_pages": sorted(
                [{"page": k, "active_users": v} for k, v in realtime_pages.items()],
                key=lambda x: x["active_users"], reverse=True
            ),
            "countries": sorted(
                [{"country": k, "active_users": v} for k, v in realtime_countries.items()],
                key=lambda x: x["active_users"], reverse=True
            )
        }
    })



# -----------------------------------


def get_flow():
    return Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'business_profile.json'),
        scopes=["https://www.googleapis.com/auth/business.manage"],
        redirect_uri=settings.GOOGLE_BUSINESS_REDIRECT_URI
    )

class AuthStartView(APIView):
    # permission_classes = [IsAuthenticated]
    def get(self, request):
        flow = get_flow()
        auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
        return redirect(auth_url)

class AuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        flow = get_flow()
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials
        GoogleBusinessToken.objects.update_or_create(
            user=request.user,
            defaults={"credentials": {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes
            }}
        )
        return Response({"message": "✅ Connected to Google Business Profile (Mock Mode)"})

class ListBusinessesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            token_obj = GoogleBusinessToken.objects.get(user=request.user)
        except GoogleBusinessToken.DoesNotExist:
            return Response({"error": "No GBP token found"}, status=400)

        creds_info = token_obj.credentials
        creds = Credentials(**creds_info)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_obj.credentials['token'] = creds.token
            token_obj.save()

        if settings.GOOGLE_BUSINESS_USE_MOCK:
            return Response({
                "accounts": [{"name": "accounts/1234567890", "accountName": "Test Business"}],
                "mode": "mock"
            })

        service = build('mybusinessaccountmanagement', 'v1', credentials=creds)
        accounts = service.accounts().list().execute()
        return Response(accounts)



