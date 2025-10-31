# services/gbp_poster.py
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from django.utils import timezone

class GBPResponsePoster:
    def __init__(self, user):
        self.user = user
    
    def post_responses(self, ai_responses, reviews):
        """Post AI responses back to Google Business Profile - mock or live based on settings"""
        try:
            from .models import GoogleBusinessToken, Review, AIResponseLog
            
            if settings.GOOGLE_BUSINESS_USE_MOCK:
                print("🔧 Using MOCK mode for response posting")
                return self._mock_post_responses(ai_responses, reviews)
            else:
                print("🚀 Using LIVE mode for response posting")
                token_obj = GoogleBusinessToken.objects.get(user=self.user)
                creds_info = token_obj.credentials
                creds = Credentials(**creds_info)
                return self._real_post_responses(creds, ai_responses, reviews)
                
        except Exception as e:
            print(f"❌ Error posting responses: {e}")
            return self._mock_post_responses(ai_responses, reviews)
    
    def _real_post_responses(self, creds, ai_responses, reviews):
        """Actually post responses to GBP API"""
        service = build('mybusiness', 'v4', credentials=creds)
        
        results = []
        for ai_resp in ai_responses:
            try:
                # Find the corresponding review to get GBP review name
                review = next((r for r in reviews if r['review_id'] == ai_resp['review_id']), None)
                
                if not review or 'gbp_review_name' not in review:
                    print(f"⚠️ Could not find GBP review name for {ai_resp['review_id']}")
                    continue
                
                review_name = review['gbp_review_name']
                response_text = ai_resp['responseText']
                
                # Post to GBP API
                result = service.accounts().locations().reviews().reply(
                    name=review_name,
                    body={'comment': response_text}
                ).execute()
                
                # Save to database
                self._save_response_to_db(review, ai_resp, response_text)
                
                results.append({
                    'review_id': ai_resp['review_id'],
                    'success': True,
                    'posted_at': timezone.now().isoformat(),
                    'mode': 'live',
                    'response_preview': response_text[:100] + '...' if len(response_text) > 100 else response_text
                })
                
                print(f"✅ Posted response to review: {ai_resp['review_id']}")
                
            except HttpError as e:
                error_msg = f"GBP API error: {e}"
                print(f"❌ {error_msg}")
                results.append({
                    'review_id': ai_resp['review_id'],
                    'success': False,
                    'error': error_msg,
                    'mode': 'live'
                })
            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                print(f"❌ {error_msg}")
                results.append({
                    'review_id': ai_resp['review_id'],
                    'success': False,
                    'error': error_msg,
                    'mode': 'live'
                })
        
        return results
    
    def _mock_post_responses(self, ai_responses, reviews):
        """Mock posting responses for testing"""
        results = []
        
        for ai_resp in ai_responses:
            try:
                # Find the corresponding review
                review = next((r for r in reviews if r['review_id'] == ai_resp['review_id']), None)
                
                # Save to database (mock)
                self._save_response_to_db(review, ai_resp, ai_resp['responseText'])
                
                results.append({
                    'review_id': ai_resp['review_id'],
                    'success': True,
                    'posted_at': timezone.now().isoformat(),
                    'mode': 'mock',
                    'response_preview': ai_resp['responseText'][:100] + '...' if len(ai_resp['responseText']) > 100 else ai_resp['responseText']
                })
                
                print(f"✅ [MOCK] Posted response to review: {ai_resp['review_id']}")
                
            except Exception as e:
                results.append({
                    'review_id': ai_resp['review_id'],
                    'success': False,
                    'error': f"Mock error: {e}",
                    'mode': 'mock'
                })
        
        return results
    
    def _save_response_to_db(self, review_data, ai_response, response_text):
        """Save response to database"""
        try:
            from .models import Review, BusinessProfile, AIResponseLog
            
            if not review_data or 'business_profile_id' not in review_data:
                return
                
            # Find or create review in database
            review, created = Review.objects.get_or_create(
                review_id=review_data['review_id'],
                defaults={
                    'business_profile_id': review_data['business_profile_id'],
                    'reviewer_name': review_data['name'],
                    'comment': review_data['comment'],
                    'star_rating': review_data['star_rating'],
                    'review_date': timezone.now(),
                    'has_response': True,
                    'response_text': response_text
                }
            )
            
            if not created:
                # Update existing review
                review.has_response = True
                review.response_text = response_text
                review.save()
            
            # Log AI response
            AIResponseLog.objects.create(
                review=review,
                request_data={
                    'review_id': review_data['review_id'],
                    'name': review_data['name'],
                    'comment': review_data['comment'],
                    'star_rating': review_data['star_rating']
                },
                response_data=ai_response
            )
            
        except Exception as e:
            print(f"⚠️ Error saving to database: {e}")