# search_console/google_service.py

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.conf import settings

from SEO_Automation.db_router import get_current_service

CLIENT_SECRET_FILE = os.path.join(settings.BASE_DIR, 'client_secrets.json')
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

def get_flow_search():
    print("IN search console flow ")
    redirect_ui = settings.GOOGLE_SEARCH_REDIRECT_URI
    service = get_current_service()
    if service == "trucking":
        redirect_ui = settings.GOOGLE_SEARCH_REDIRECT_URI_TRUCKING
    else:
        redirect_ui = settings.GOOGLE_SEARCH_REDIRECT_URI

    return Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_ui
    )

def build_service(credentials_info):
    creds = Credentials.from_authorized_user_info(credentials_info, SCOPES)
    return build('searchconsole', 'v1', credentials=creds)
