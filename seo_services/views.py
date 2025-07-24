from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from seo_services.scrape import get_paa_questions
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
from rest_framework.permissions import IsAdminUser


logger = logging.getLogger(__name__)

class PackageCreateAPIView(APIView):
    def post(self, request):
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            price_usd = Decimal(request.data.get("price_usd", 0))
            package = serializer.save(price=price_usd)

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
    
    def get(self, request, pk=None):
        if pk:
            package = get_object_or_404(Package, pk=pk)
            serializer = PackageSerializer(package)
            return Response(serializer.data, status=status.HTTP_200_OK)
        packages = Package.objects.all()
        serializer = PackageSerializer(packages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        
        # ✅ Add Keyword Optimization Task
        SEOTask.objects.create(
            user=user,
            service_page=service_page,
            task_type="keyword_optimization",
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

        # 🔁 Monthly count logic
        current_month = timezone.now().strftime('%Y-%m')
        if task.month_year != current_month:
            task.count_this_month = 0
            task.month_year = current_month

        task.count_this_month += 1

        interval_days = onboarding.package.interval if onboarding.package else 7
        task.ai_request_payload = ai_payload
        task.ai_response_payload = data
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=interval_days)
        # task.next_run = timezone.now() + timezone.timedelta(minutes=3)
        task.status = "completed"
        task.save()


        logger.info(f"✅ Task {task.id} completed successfully.")
        try:
            upload_blog_to_wordpress(blog, task.service_page.wordpress_connection)
        
        except Exception as e:
            logger.exception(f"❌ Wordpress blog upload failed: {str(e)}")


        # 🔁 Auto-create next task if blog limit not reached
        # 🔁 Auto-create next blog task if blog limit not reached
        package = onboarding.package
        if task.is_active and  task.count_this_month < package.blog_limit:
            SEOTask.objects.create(
                user=user,
                service_page=task.service_page,
                task_type='blog_writing',
                next_run=task.last_run + timedelta(days=package.interval),
                # next_run = timezone.now() + timezone.timedelta(minutes=3),
                status='pending',
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True
            )
            logger.info(f"✅ New blog writing task created (this_month_count={task.count_this_month})")
        else:
            
            # ✅ Limit hit: Pause next task, will resume next month
            SEOTask.objects.create(
                user=user,
                service_page=task.service_page,
                task_type='blog_writing',
                next_run=None,
                status='pending',
                count_this_month=0,  # new month will reset this
                month_year=current_month,
                is_active=True
            )
            logger.info(f"⏸️ Blog limit reached. Next task paused until new month.")

    except Exception as e:
        logger.exception(f"❌ Exception in run_blog_writing for task {task.id}: {str(e)}")
        task.status = "failed"
        task.ai_response_payload = {"error": str(e)}
        task.save()


def run_seo_optimization(task):
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"🚀 Running SEO optimization task for Task ID {task.id}")
        service_page = task.service_page
        user = task.user

        onboarding = OnboardingForm.objects.filter(user=user).first()
        if not onboarding:
            logger.warning("⚠️ No onboarding form found.")
            task.status = "failed"
            task.save()
            return
        
        #  Monthly check
        current_month = timezone.now().strftime("%Y-%m")
        package_limit = onboarding.package.seo_optimization_limit if onboarding.package else 5  # adjust default if needed

        
        if task.month_year != current_month:
            task.count_this_month = 0
            task.month_year = current_month

        # Check if limit reached
        if task.count_this_month >= package_limit:
            logger.warning("🚫 SEO task limit reached for this month.")
            task.status = "skipped"
            task.save()
            return

        # 🔑 Get all keywords related to services for this user
        keywords = Keyword.objects.filter(
            service__onboarding_form=onboarding
        ).values_list("keyword", flat=True)

        if not keywords:
            logger.warning("⚠️ No keywords found for SEO optimization.")
            task.status = "failed"
            task.save()
            return

        # 🌐 Fetch current HTML content from service page URL
        try:
            page_response = requests.get(service_page.page_url, timeout=20)
            page_response.raise_for_status()
            page_content = page_response.text
        except Exception as e:
            logger.exception(f"❌ Failed to fetch page content: {str(e)}")
            task.status = "failed"
            task.ai_response_payload = {"error": str(e)}
            task.save()
            return

        # 📡 Send to optimization API
        api_payload = {
            "keywords": list(keywords),
            "content": page_content,
        }

        api_response = requests.post(
            f"{settings.AI_API_DOMAIN}/optimize_blog",
            json=api_payload,
            timeout=60
        )

        if api_response.status_code != 200:
            logger.error(f"❌ API response error: {api_response.text}")
            task.status = "failed"
            task.ai_request_payload = api_payload
            task.ai_response_payload = {"error": api_response.text}
            task.save()
            return

        optimized_data = api_response.json()
        optimized_content = optimized_data.get("optimizedBlog")
        logger.info("📝 optimized content: %s", optimized_content)

        if not optimized_content:
            logger.warning("⚠️ No optimized content received.")
            task.status = "failed"
            task.save()
            return

        # ✅ Save optimized content
        task.optimized_content = optimized_content
        task.ai_request_payload = api_payload
        task.ai_response_payload = optimized_data
        task.status = "completed"
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=onboarding.package.interval if onboarding.package else 7)
        task.month_year = current_month
        task.count_this_month +=1 
        task.save()

        logger.info(f"✅ SEO Optimization Task {task.id} completed and saved.")

        try:
            upload_service_page_to_wordpress(task.service_page, task.optimized_content)
        
        except Exception as e:
            logger.exception(f"❌ Wordpress blog upload failed: {str(e)}")

        # create next task 
        if task.count_this_month < package_limit:
            SEOTask.objects.create(
                user=user,
                service_page=service_page,
                task_type='seo_optimization',
                next_run=task.next_run,
                status='pending',
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True,
            )
            logger.info("✅ Created next SEO task.")
        else:
            SEOTask.objects.create(
                user=user,
                service_page=service_page,
                task_type='seo_optimization',
                next_run=None,
                status='pending',
                count_this_month=0,
                month_year=current_month,
                is_active=True,
            )
            logger.info("⏸️ Limit reached, next SEO task paused for this month.")    

    except Exception as e:
        logger.exception(f"❌ Exception in SEO Optimization task: {str(e)}")
        task.status = "failed"
        task.ai_response_payload = {"error": str(e)}
        task.save()

def run_keyword_optimization(task):
    logger = logging.getLogger(__name__)
    logger.info("🔍 Running keyword optimization task...")

    try:
        user = task.user
        onboarding = OnboardingForm.objects.filter(user=user).first()
        if not onboarding:
            logger.warning(f"⚠️ No onboarding form found for user {user.email}")
            task.status = "failed"
            task.save()
            return
        
        # Monthly limit check
        current_month = timezone.now().strftime("%Y-%m")
        package_limit = onboarding.package.keyword_limit if onboarding.package else 5  # Default if missing

        if task.month_year == current_month and task.count_this_month >= package_limit:
            logger.warning(f"🚫 Keyword optimization limit reached for this month.")
            task.status = "skipped"
            task.next_run = None
            task.save()

            SEOTask.objects.create(
                user=user,
                task_type="keyword_optimization",
                status="pending",
                is_active=True,
                month_year=current_month,
                count_this_month=0,
                next_run=None,
            )
            logger.info("⏸️ Limit reached, next keyword task paused for this month.")
            return

        services = onboarding.services.all()
        if not services:
            logger.warning(f"⚠️ No services found for onboarding form {onboarding.id}")
            task.status = "failed"
            task.save()
            return

        for service in services:
            keywords = list(service.keywords.values_list("keyword", flat=True))
            if not keywords:
                logger.warning(f"⚠️ No keywords found for service {service.id}")
                continue

            ai_payload = {"keywords": keywords}
            try:
                response = requests.post(
                    f"{settings.AI_API_DOMAIN}/keyword_suggestions_multiple",
                    json=ai_payload,
                    timeout=30
                )
                if response.status_code != 200:
                    logger.warning(f"⚠️ AI response error for service {service.id}: {response.text}")
                    continue

                try:
                    data = response.json()
                except Exception as parse_error:
                    logger.warning(f"⚠️ Failed to parse JSON for service {service.id}: {parse_error}")
                    continue

                suggestions = data.get("suggested_keywords", {})

                if not isinstance(suggestions, dict):
                    logger.warning(f"⚠️ Invalid AI response for service {service.id}: {suggestions}")
                    continue

                for original_keyword, suggestion_list in suggestions.items():
                    if not suggestion_list:
                        logger.info(f"ℹ️ No suggestions returned for keyword '{original_keyword}'")
                        continue

                    # Pick keyword with highest search volume
                    best_keyword = max(suggestion_list, key=lambda k: k.get("search_volume", 0))
                    new_keyword = best_keyword["keyword"]

                    if new_keyword and new_keyword != original_keyword:
                        keyword_obj = Keyword.objects.filter(service=service, keyword=original_keyword).first()
                        if keyword_obj:
                            logger.info(f"🔄 Replacing keyword '{original_keyword}' with '{new_keyword}' (volume: {best_keyword['search_volume']})")
                            keyword_obj.keyword = new_keyword
                            keyword_obj.save()

                            KeywordQuestion.objects.filter(keyword=keyword_obj).delete()  # Clear old ones
                            try:
                                questions = get_paa_questions(new_keyword)
                                for q in questions:
                                    KeywordQuestion.objects.create(keyword=keyword_obj, question=q)
                                logger.info(f"Saved {len(questions)} questions for keyword: {new_keyword}")
                            except Exception as e:
                                logger.error(f"Failed to save questions for keyword {new_keyword}: {str(e)}")
                                continue
                        else:
                            logger.warning(f"⚠️ Keyword object not found for '{original_keyword}' in service {service.id}")
                    else:
                        logger.info(f"✅ Keeping keyword '{original_keyword}' as is (volume: {best_keyword['search_volume']})")
                        keyword_obj = Keyword.objects.filter(service=service, keyword=original_keyword).first()
                        if keyword_obj:
                            logger.info(f"🔍 Found keyword object: {keyword_obj.keyword}, Checking if questions exist...")

                        if keyword_obj and not keyword_obj.questions.exists():
                            try:
                                questions = get_paa_questions(original_keyword)
                                for q in questions:
                                    KeywordQuestion.objects.create(keyword=keyword_obj, question=q)
                                logger.info(f"📝 Saved {len(questions)} PAA questions for existing keyword: {original_keyword}")
                            except Exception as e:
                                logger.error(f"⚠️ Failed to save questions for keyword {original_keyword}: {str(e)}")
                        else:
                            if keyword_obj:
                                logger.info(f"📌 Skipping PAA fetch — questions already exist for: {original_keyword}")

            except Exception as e:
                logger.exception(f"❌ Failed optimizing keywords for service {service.id}: {e}")

        # Mark task complete
        task.status = "completed"
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=onboarding.package.interval if onboarding.package else 7)
        # task.next_run = timezone.now() + timezone.timedelta(minutes=3)
        task.month_year = current_month
        task.count_this_month = (task.count_this_month or 0) + 1
        task.save()
        logger.info(f"✅ Keyword optimization task {task.id} completed.")

        # ✅ Create next task (Active or Paused based on usage)
        if task.count_this_month <= package_limit:
            SEOTask.objects.create(
                user=user,
                task_type="keyword_optimization",
                next_run=task.next_run,
                status="pending",
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True,
            )
            logger.info("✅ Created next keyword optimization task.")
        else:
            SEOTask.objects.create(
                user=user,
                task_type="keyword_optimization",
                next_run=None,
                status="pending",
                count_this_month=0,
                month_year=current_month,
                is_active=True,
            )
            logger.info("⏸️ Limit reached, next keyword task paused for this month.")

    except Exception as e:
        logger.exception(f"❌ Exception in run_keyword_optimization for task {task.id}: {str(e)}")
        task.status = "failed"
        task.ai_response_payload = {"error": str(e)}
        task.save()



class StopAutomation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        action = request.data.get("action")

        if not action:
            return Response({"success": False, "message": "action is required."}, status=400)

        task_type_map = {
            "keywords": "keyword_optimization",
            "blog": "blog_writing",
            "seo": "seo_optimization"
        }

        task_type = task_type_map.get(action)
        if not task_type:
            return Response({"success": False, "message": "Invalid action."}, status=400)
        tasks = SEOTask.objects.filter(user=user, task_type=task_type, is_active=True)
        if not tasks.exists():
            return Response({"success": False, "message": f"No active {action} tasks found for user."}, status=404)

        tasks.update(is_active=False)
        return Response({"success": True, "message": f"{action.capitalize()} stopped successfully."})
    


class StartAutomation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        action = request.data.get("action")

        if not action:
            return Response({"success": False, "message": "Action is required."}, status=400)

        valid_actions = {
            "blog": "blog_writing",
            "seo": "seo_optimization",
            "keywords": "keyword_optimization"
        }

        task_type = valid_actions.get(action)
        if not task_type:
            return Response({"success": False, "message": "Invalid action provided."}, status=400)

        # Get all inactive tasks of that type for the user
        tasks = SEOTask.objects.filter(user=user, task_type=task_type, is_active=False)
        if not tasks.exists():
            return Response({"success": False, "message": f"No inactive {action} tasks found for user."}, status=404)

        # Activate all those tasks
        tasks.update(is_active=True)

        return Response({"success": True, "message": f"{action.capitalize()} automation started successfully."})


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

# admin 
class AdminClientListAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.filter(user_type='user')
        serializer = AdminClientDetailSerializer(users, many=True)
        return Response(serializer.data)
