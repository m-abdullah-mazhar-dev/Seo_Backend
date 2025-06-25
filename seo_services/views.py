from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from.serializers import *
from rest_framework.response import Response
from rest_framework import status
import base64 , requests
from datetime import timedelta
from django.utils import timezone




class OnBoardingFormAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        print(request.user, "********** USER IN VIEW **********")
        print(request.auth, "********** AUTH **********")

        serializer = OnBoardingFormSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Onboarding form submitted successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "errors": serializer.errors,
                "message": "Invalid data provided."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    
    def get(self, request, pk=None):
        if pk:
            try:
                onboarding_form = OnboardingForm.objects.get(pk=pk, user=request.user)
                serializer = OnBoardingFormSerializer(onboarding_form)
                return Response({"message": "Onboarding form retrieved successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
            except OnboardingForm.DoesNotExist:
                return Response({"message": "Onboarding form not found."}, status=status.HTTP_404_NOT_FOUND)

        onboarding_forms = OnboardingForm.objects.filter(user=request.user)
        serializer = OnBoardingFormSerializer(onboarding_forms, many=True)
        return Response({"message": "Onboarding forms retrieved successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
    
    
    def patch(self, request, pk=None):
        if not pk:
            return Response({"message": "Onboarding form ID is required for update."}, status=status.HTTP_400_BAD_REQUEST)

        onboarding_form = get_object_or_404(OnboardingForm, pk=pk, user=request.user)

        serializer = OnBoardingFormSerializer(
            onboarding_form,
            data=request.data,
            partial=True,  # Allow partial updates
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Onboarding form updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK
            )

        return Response(
            {"errors": serializer.errors, "message": "Invalid data provided."},
            status=status.HTTP_400_BAD_REQUEST
        )


# def generate_wordpress_token(username, application_password):
#     credentials = f"{username}:{application_password}"
#     token = base64.b64encode(credentials.encode()).decode()
#     return token


# class ConnectWordPressAPI(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         site_url = request.data.get('site_url')
#         username = request.data.get('username').strip()
#         app_password = request.data.get('app_password').strip()

#         if not all([site_url, username, app_password]):
#             return Response({"error": "Missing required fields."}, status=400)

#         token = generate_wordpress_token(username, app_password)

#         wp_conn, created = WordPressConnection.objects.update_or_create(
#             user=request.user,
#             defaults={
#                 'site_url': site_url,
#                 'username': username,         # ✅ Save username
#                 'app_password': app_password, # ✅ Save app password
#                 'access_token': token         # ✅ Optional
#             }
#         )

#         return Response({"message": "WordPress connected successfully."})

    
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from requests.auth import HTTPBasicAuth
# from requests.exceptions import RequestException
# import requests

# class VerifyWordPressConnectionAPI(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         try:
#             wp_conn = request.user.wordpress_connection
#             print(type(wp_conn))
#         except WordPressConnection.DoesNotExist:
#             return Response({"error": "WordPress connection not found."}, status=404)

#         url = f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/users/me"

#         try:
#             print("Username: ", wp_conn.username.strip())
#             print("App Password: ", wp_conn.app_password.strip())
#             print("URL: ", url)

#             # ✅ Correct way for WordPress App Passwords
#             response = requests.get(url, auth=HTTPBasicAuth("Arqureshii7121@gmail.com", wp_conn.app_password.strip()))

#             if response.status_code == 200:
#                 return Response({"message": "Connection is valid."})
#             else:
#                 return Response({
#                     "error": "Invalid connection.",
#                     "status_code": response.status_code,
#                     "response": response.text
#                 }, status=response.status_code)

#         except RequestException as e:
#             return Response({"error": "Connection failed.", "details": str(e)}, status=500)
def generate_wordpress_token(username, application_password):
    credentials = f"{username}:{application_password}"
    token = base64.b64encode(credentials.encode()).decode()
    return token


class ConnectWordPressAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        site_url = request.data.get('site_url')
        username = request.data.get('username', '').strip()
        app_password = request.data.get('app_password', '').strip()

        if not all([site_url, username, app_password]):
            return Response({"error": "Missing required fields."}, status=400)

        # 🔹 Generate and store the access token (base64 encoded)
        access_token = generate_wordpress_token(username, app_password)

        wp_conn, created = WordPressConnection.objects.update_or_create(
            user=request.user,
            defaults={
                'site_url': site_url,
                'access_token': access_token  # ✅ Now we only need the token
            }
        )

        return Response({"message": "WordPress connected successfully."})


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from requests.exceptions import RequestException
import requests

class VerifyWordPressConnectionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            wp_conn = request.user.wordpress_connection
            print(type(wp_conn))
        except WordPressConnection.DoesNotExist:
            return Response({"error": "WordPress connection not found."}, status=404)

        url = f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/users/me"

        try:
            # 🔹 Prepare the Authorization Header
            headers = {
                'Authorization': f'Basic {wp_conn.access_token.strip()}'
            }

            print("URL: ", url)
            print("Access Token: ", wp_conn.access_token.strip())

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return Response({"message": "Connection is valid."})
            else:
                return Response({
                    "error": "Invalid connection.",
                    "status_code": response.status_code,
                    "response": response.text
                }, status=response.status_code)

        except RequestException as e:
            return Response({"error": "Connection failed.", "details": str(e)}, status=500)


class SubmitServicePageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        page_url = request.data.get("page_url")
        blog_required = request.data.get("blog_required", False)

        if not page_url:
            return Response({"error": "Page URL is required."}, status=400)

        # Check if user has connected WordPress
        try:
            wp_conn = user.wordpress_connection
        except WordPressConnection.DoesNotExist:
            return Response({"error": "User has not connected WordPress."}, status=400)

        # Create the Service Page
        service_page = ServicePage.objects.create(
            user=user,
            wordpress_connection=wp_conn,
            page_url=page_url,
            blog_required=blog_required
        )

        # Get interval from user's package
        onboarding_form = OnboardingForm.objects.filter(user=user).first()
        if not onboarding_form or not onboarding_form.package:
            return Response({"error": "User package not found."}, status=400)

        interval_days = onboarding_form.package.interval
        next_run = timezone.now() + timedelta(days=interval_days)

        # Create SEO Optimization Task
        SEOTask.objects.create(
            user=user,
            service_page=service_page,
            task_type="seo_optimization",
            next_run=next_run
        )

        # Create Blog Writing Task (if blog_required)
        if blog_required:
            SEOTask.objects.create(
                user=user,
                service_page=service_page,
                task_type="blog_writing",
                next_run=next_run
            )

        return Response({"message": "Service Page & Tasks created successfully."})