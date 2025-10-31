# services/review_fetcher.py
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from django.utils import timezone
from datetime import datetime

class ReviewFetcher:
    def __init__(self, user):
        self.user = user
    
    def fetch_reviews(self):
        """Fetch reviews from ALL connected business profiles - mock or live based on settings"""
        all_reviews = []
        
        try:
            from .models import GoogleBusinessToken, BusinessProfile
            token_obj = GoogleBusinessToken.objects.get(user=self.user)
            
            if settings.GOOGLE_BUSINESS_USE_MOCK:
                print("🔧 Using MOCK mode for review fetching")
                # Get all business profiles for user and fetch mock reviews for each
                business_profiles = BusinessProfile.objects.filter(user=self.user, is_active=True)
                if not business_profiles.exists():
                    # Create mock business profile if none exists
                    business_profiles = [self._create_mock_business_profile()]
                
                for profile in business_profiles:
                    reviews = self._get_mock_reviews_for_profile(profile)
                    all_reviews.extend(reviews)
            else:
                print("🚀 Using LIVE mode for review fetching")
                # Get real reviews from all connected profiles
                creds_info = token_obj.credentials
                creds = Credentials(**creds_info)
                all_reviews = self._get_real_reviews_from_all_profiles(creds)
                
        except GoogleBusinessToken.DoesNotExist:
            print("⚠️ No GBP token found - using mock reviews")
            all_reviews = self._get_mock_reviews_for_profile(None)
        except Exception as e:
            print(f"❌ Error fetching reviews: {e}")
            all_reviews = self._get_mock_reviews_for_profile(None)
        
        return all_reviews
    
    def _create_mock_business_profile(self):
        """Create a mock business profile if none exists"""
        from .models import BusinessProfile
        profile = BusinessProfile.objects.create(
            user=self.user,
            account_id='mock_account_123',
            location_id='mock_location_1',
            location_name='Test HVAC Services',
            description='Local HVAC repair and maintenance services'
        )
        return profile
    
    def _get_mock_reviews_for_profile(self, profile):
        """Return mock reviews for a business profile"""
        return [
            {
                "review_id": f"rvw_{profile.location_id if profile else '1'}_1",
                "name": "Ahsan",
                "comment": "Tech arrived late and issue wasn't fixed.",
                "star_rating": 2,
                "review_date": "2024-01-15T10:00:00Z",
                "business_profile_id": profile.id if profile else None
            },
            {
                "review_id": f"rvw_{profile.location_id if profile else '1'}_2",
                "name": "Sara",
                "comment": "Excellent service and very friendly team!",
                "star_rating": 5,
                "review_date": "2024-01-14T15:30:00Z",
                "business_profile_id": profile.id if profile else None
            },
            {
                "review_id": f"rvw_{profile.location_id if profile else '1'}_3", 
                "name": "Bilal",
                "comment": "Good overall, but they forgot to clean up after the repair.",
                "star_rating": 4,
                "review_date": "2024-01-13T09:15:00Z",
                "business_profile_id": profile.id if profile else None
            }
        ]
    
    def _get_real_reviews_from_all_profiles(self, creds):
        """Get real reviews from ALL business profiles via GBP API"""
        try:
            service = build('mybusiness', 'v4', credentials=creds)
            all_reviews = []
            
            # Get all accounts
            accounts_response = service.accounts().list().execute()
            accounts = accounts_response.get('accounts', [])
            
            for account in accounts:
                # Get all locations for this account
                locations_response = service.accounts().locations().list(
                    parent=account['name']
                ).execute()
                locations = locations_response.get('locations', [])
                
                for location in locations:
                    # Get or create business profile in database
                    profile = self._get_or_create_business_profile(account, location)
                    
                    # Get reviews for this location
                    reviews_response = service.accounts().locations().reviews().list(
                        parent=location['name']
                    ).execute()
                    reviews = reviews_response.get('reviews', [])
                    
                    for review in reviews:
                        all_reviews.append({
                            "review_id": review['reviewId'],
                            "name": review['reviewer'].get('displayName', 'Anonymous'),
                            "comment": review.get('comment', ''),
                            "star_rating": review.get('starRating', 0),
                            "review_date": review.get('createTime'),
                            "business_profile_id": profile.id,
                            "gbp_review_name": review['name']  # For posting responses back
                        })
            
            return all_reviews
            
        except HttpError as e:
            print(f"❌ Google API error: {e}")
            return self._get_mock_reviews_for_profile(None)
    
    def _get_or_create_business_profile(self, account, location):
        """Get or create business profile in database"""
        from .models import BusinessProfile
        
        account_id = account['name'].split('/')[-1]
        location_id = location['name'].split('/')[-1]
        
        profile, created = BusinessProfile.objects.get_or_create(
            user=self.user,
            location_id=location_id,
            defaults={
                'account_id': account_id,
                'location_name': location.get('locationName', 'Unknown Business'),
                'description': location.get('address', '')
            }
        )
        
        if created:
            print(f"✅ Created business profile: {profile.location_name}")
        
        return profile