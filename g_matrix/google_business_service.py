# services/google_business_service.py
import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import requests
import logging
from google.auth.transport.requests import Request


logger = logging.getLogger(__name__)

class GoogleBusinessService:
    def __init__(self, credentials_info):
        self.credentials = Credentials(**credentials_info)
        if self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())
        self.service = build('mybusiness', 'v4', credentials=self.credentials)
    
    def get_accounts(self):
        """Get all business accounts for the authenticated user"""
        if settings.GOOGLE_BUSINESS_USE_MOCK:
            return self._get_mock_accounts()
        
        try:
            accounts = self.service.accounts().list().execute()
            return accounts.get('accounts', [])
        except HttpError as e:
            logger.error(f"Error fetching accounts: {e}")
            return []
    
    def get_locations(self, account_name):
        """Get all locations for a business account"""
        if settings.GOOGLE_BUSINESS_USE_MOCK:
            return self._get_mock_locations()
        
        try:
            locations = self.service.accounts().locations().list(
                parent=account_name
            ).execute()
            return locations.get('locations', [])
        except HttpError as e:
            logger.error(f"Error fetching locations: {e}")
            return []
    
    def get_reviews(self, location_name):
        """Get reviews for a specific location"""
        if settings.GOOGLE_BUSINESS_USE_MOCK:
            return self._get_mock_reviews()
        
        try:
            reviews = self.service.accounts().locations().reviews().list(
                parent=location_name
            ).execute()
            return reviews.get('reviews', [])
        except HttpError as e:
            logger.error(f"Error fetching reviews: {e}")
            return []
    
    def post_response(self, location_name, review_name, response_text):
        """Post response to a review"""
        if settings.GOOGLE_BUSINESS_USE_MOCK:
            return self._mock_post_response()
        
        try:
            response = self.service.accounts().locations().reviews().reply(
                name=review_name,
                body={'comment': response_text}
            ).execute()
            return response
        except HttpError as e:
            logger.error(f"Error posting response: {e}")
            return None
    
    def _get_mock_accounts(self):
        return [
            {
                "name": "accounts/1234567890",
                "accountName": "Test Business Account",
                "type": "PERSONAL"
            }
        ]
    
    def _get_mock_locations(self):
        return [
            {
                "name": "accounts/1234567890/locations/1",
                "locationName": "Test HVAC Business",
                "address": "123 Test St, Test City"
            }
        ]
    
    def _get_mock_reviews(self):
        return [
            {
                "name": "accounts/1234567890/locations/1/reviews/rvw_1",
                "reviewId": "rvw_1",
                "reviewer": {"displayName": "Ahsan"},
                "starRating": 2,
                "comment": "Tech arrived late and issue wasn't fixed.",
                "createTime": "2024-01-15T10:00:00Z"
            },
            {
                "name": "accounts/1234567890/locations/1/reviews/rvw_2",
                "reviewId": "rvw_2",
                "reviewer": {"displayName": "Sara"},
                "starRating": 5,
                "comment": "Excellent service and very friendly team!",
                "createTime": "2024-01-14T15:30:00Z"
            },
            {
                "name": "accounts/1234567890/locations/1/reviews/rvw_3",
                "reviewId": "rvw_3",
                "reviewer": {"displayName": "Bilal"},
                "starRating": 4,
                "comment": "Good overall, but they forgot to clean up after the repair.",
                "createTime": "2024-01-13T09:15:00Z"
            }
        ]
    
    def _mock_post_response(self):
        return {"status": "success", "message": "Mock response posted successfully"}