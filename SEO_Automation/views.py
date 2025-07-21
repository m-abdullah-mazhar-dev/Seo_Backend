# views.py
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken

class GoogleLoginJWTOny(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        # Force JWT response (disable session key)
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = self.user
            refresh = RefreshToken.for_user(user)
            response.data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'pk': user.pk,
                    'email': user.email,
                    # 'username': user.username,
                }
            }
        return response