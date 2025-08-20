# # seo/tasks.py
# from celery import shared_task
# from django.utils import timezone
# from .models import SEOTask
# from .views import run_blog_writing

# @shared_task
# def process_due_seo_tasks():
#     now = timezone.now()
#     print(now)
#     tasks = SEOTask.objects.filter(next_run__lte=now, status='pending')
#     print(tasks)

#     for task in tasks:
#         if task.task_type == 'seo_optimization':
#             continue
#         elif task.task_type == 'blog_writing':
#             print("running blog tasks")
#             run_blog_writing(task)


import logging
import requests
from celery import shared_task
from django.utils import timezone
from .models import SEOTask, OnboardingForm, Keyword, Blog, BlogImage
from .views import run_blog_writing, run_gmb_post_creation, run_keyword_optimization, run_seo_optimization  # or move logic here if you prefer
from datetime import timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def process_due_seo_tasks():
    logger.info(f"🔄SEO tasks started.")
    now = timezone.now()
    tasks = SEOTask.objects.filter(next_run__lte=now, status='pending', is_active=True)
    # tasks = SEOTask.objects.filter(status='pending')
    logger.info(f"🔄 Found {tasks.count()} due SEO tasks to process.")

    for task in tasks:
        logger.info(f"📌 Processing Task ID {task.id} for user {task.user.email}")
        try:
            if task.task_type == 'seo_optimization':
                pass 
                logger.info("⏭️ Running SEO Optimization task")
                run_seo_optimization(task)
            elif task.task_type == 'blog_writing':
                pass 
                logger.info("✍️ Running blog writing task...")
                run_blog_writing(task)
            
            elif task.task_type == 'keyword_optimization':
                logger.info("🔍 Running keyword optimization task...")
                run_keyword_optimization(task)
            elif task.task_type == 'gmb_post':
                logger.info("📢 Running GMB post creation task...")
                run_gmb_post_creation(task)

        except Exception as e:
            logger.error(f"❌ Failed processing task ID {task.id}: {str(e)}")


@shared_task
def reactivate_monthly_blog_tasks():
    logger = logging.getLogger(__name__)
    logger.info("🔁 Checking for monthly reset of blog tasks...")
    current_month = timezone.now().strftime('%Y-%m')
    
    paused_tasks = SEOTask.objects.filter(
        # task_type='blog_writing',
        next_run=None,
        status='pending',
        is_active=True
    )
    
    for task in paused_tasks:
        if task.month_year != current_month:
            logger.info(f"✅ Reactivating Task {task.id} (new month)")
            task.count_this_month = 0
            task.month_year = current_month
            task.next_run = timezone.now()
            task.save()
        logger.info(f"months are same {current_month} -- {task.month_year}")