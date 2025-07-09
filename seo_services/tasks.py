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
from .views import run_blog_writing, run_seo_optimization  # or move logic here if you prefer
from datetime import timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def process_due_seo_tasks():
    logger.info(f"🔄SEO tasks started.")
    now = timezone.now()
    tasks = SEOTask.objects.filter(next_run__lte=now, status='pending')
    # tasks = SEOTask.objects.filter(status='pending')
    logger.info(f"🔄 Found {tasks.count()} due SEO tasks to process.")

    for task in tasks:
        logger.info(f"📌 Processing Task ID {task.id} for user {task.user.email}")
        try:
            if task.task_type == 'seo_optimization':
                logger.info("⏭️ Running SEO Optimization task")
                run_seo_optimization(task)
            elif task.task_type == 'blog_writing':
                logger.info("✍️ Running blog writing task...")
                run_blog_writing(task)
        except Exception as e:
            logger.error(f"❌ Failed processing task ID {task.id}: {str(e)}")
