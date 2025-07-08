from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from seo_services.upload_blog_to_wp import *
from.serializers import *
from rest_framework.response import Response
from rest_framework import status
import base64 , requests
from datetime import timedelta
from django.utils import timezone
from SEO_Automation import settings
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import re
from .utils import create_stripe_product_and_price


logger = logging.getLogger(__name__)

class PackageCreateAPIView(APIView):
    def post(self, request):
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            package = serializer.save()

            # You must pass amount in cents, for example: $49.99 = 4999
            try:
                amount_cents = int(request.data.get("price_usd", 0)) * 100
                if amount_cents <= 0:
                    return Response({"error": "Valid price_usd required"}, status=400)

                product_id, price_id = create_stripe_product_and_price(
                    package, amount_cents=amount_cents
                )

                package.stripe_product_id = product_id
                package.stripe_price_id = price_id
                package.save()

                return Response(PackageSerializer(package).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                package.delete()  # Cleanup on error
                return Response({"error": str(e)}, status=500)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        next_run = timezone.now()
        print(next_run)
        # next_run = timezone.now() + timedelta(days=interval_days)

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



def run_blog_writing(task):
    logger = logging.getLogger(__name__)
    try:
        service = task.service_page
        user = task.user

        onboarding = OnboardingForm.objects.filter(user=user).first()
        if not onboarding:
            logger.warning("⚠️ No onboarding form found.")
            task.status = "failed"
            task.save()
            return

        keywords = Keyword.objects.filter(
            service__onboarding_form=onboarding
        ).values_list('keyword', flat=True)

        logger.info(f"🔑 Keywords for blog generation: {list(keywords)}")

        if not keywords:
            task.status = "failed"
            task.save()
            return

        ai_payload = {
            "keywords": list(keywords)
        }

        response = requests.post(
            f"{settings.AI_API_DOMAIN}/generate_blog_and_image",
            json=ai_payload,
            timeout=60
        )

        if response.status_code != 200:
            logger.error(f"❌ AI response error: {response.text}")
            task.status = "failed"
            task.ai_request_payload = ai_payload
            task.ai_response_payload = {"error": response.text}
            task.save()
            return
        
        data = response.json()

        blog_html = data.get("blog", "").strip()
        image_url_raw = data.get("imageUrl", "")
        image_url = re.sub(r"win\s+dows", "windows", image_url_raw)

        # Remove ```html markdown wrapper
        if blog_html.startswith("```html"):
            blog_html = blog_html.replace("```html", "").replace("```", "").strip()

        # Extract <title>
        soup = BeautifulSoup(blog_html, "html.parser")
        title = soup.title.string.strip() if soup.title else "Untitled Blog"

        logger.info("✅ Blog HTML received")
        logger.info("📝 Blog HTML: %s", blog_html)
        logger.info(f"🖼️ Image URL: {image_url}")
        logger.info(f"📝 Blog Title: {title}")

     

        blog = Blog.objects.create(
            seo_task=task,
            title=title,
            content=blog_html
        )

        if image_url:
            BlogImage.objects.create(blog=blog, image_url=image_url)

        interval_days = onboarding.package.interval if onboarding.package else 7
        task.ai_request_payload = ai_payload
        task.ai_response_payload = data
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=interval_days)
        task.status = "completed"
        task.save()

        logger.info(f"✅ Task {task.id} completed successfully.")
        try:
            upload_blog_to_wordpress(blog, task.service_page.wordpress_connection)
        
        except Exception as e:
            logger.exception(f"❌ Wordpress blog upload failed: {str(e)}")


            # 🔁 Auto-create next task if blog limit not reached
        user = task.user
        package = user.onboardingform.first().package
        # Count previous blog tasks for this page
        total_blogs = SEOTask.objects.filter(
            user=user,
            service_page=task.service_page,
            task_type='blog_writing'
        ).count()

        if total_blogs < package.blog_limit:
            SEOTask.objects.create(
                user=user,
                service_page=task.service_page,
                task_type='blog_writing',
                next_run=task.last_run + timedelta(days=package.interval),
                status='pending'
            )
            logger.info(f"✅ New Task created.")
    except Exception as e:
        logger.exception(f"❌ Exception in run_blog_writing for task {task.id}: {str(e)}")
        task.status = "failed"
        task.ai_response_payload = {"error": str(e)}
        task.save()



# Get Apis ---------------------------
class MyServiceAreasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        onboarding = request.user.onboardingform.first()
        if not onboarding:
            return Response({"success": False, "message": "Onboarding not found.", "data": []})

        service_areas = onboarding.service_areas.all()
        serializer = ServiceAreaSerializer(service_areas, many=True)
        return Response({"success": True, "message": "Service areas retrieved successfully.", "data": serializer.data})


class MyKeywordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        onboarding = request.user.onboardingform.first()
        if not onboarding:
            return Response({"success": False, "message": "Onboarding not found.", "data": []})

        keywords = Keyword.objects.filter(service__onboarding_form=onboarding)
        serializer = KeywordSerializer(keywords, many=True)
        return Response({"success": True, "message": "Keywords retrieved successfully.", "data": serializer.data})


class MyBlogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        blogs = Blog.objects.filter(seo_task__user=request.user)
        serializer = BlogSerializer(blogs, many=True)
        return Response({"success": True, "message": "Blogs retrieved successfully.", "data": serializer.data})
    
    
# ----------------