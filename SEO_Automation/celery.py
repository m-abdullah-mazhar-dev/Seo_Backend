import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SEO_Automation.settings')

app = Celery('SEO_Automation')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Timezone configuration
app.conf.enable_utc = False
app.conf.timezone = 'Asia/Karachi'

# Beat Schedule Definition
app.conf.beat_schedule = {
    'process-due-seo-tasks-every-minute': {
        'task': 'seo_services.tasks.process_due_seo_tasks',
        'schedule': crontab(minute='*/5'),
        # 'schedule': crontab(),  # Runs every minute
        'args': (),  # You can pass arguments if needed
    },
    'process-due-job-tasks-every-minute': {
        'task': 'seo_services.tasks.process_due_job_tasks',
        'schedule': crontab(minute='*/5'),
        'args': (),  # You can pass arguments if needed
    },
    'reactivate-monthly-blog-tasks': {
        'task': 'seo_services.tasks.reactivate_monthly_blog_tasks',
        # 'schedule': crontab(minute='*/5'),
        'schedule': crontab(minute=0, hour=0),  # every day at midnight
    },
    'process-search-console-keyword-tasks': {
        'task': 'g_matrix.tasks.sync_all_user_keywords',
        # 'schedule': crontab(),  # Runs every minute
        'schedule': crontab(minute=0, hour=0),  # every day at midnight
    },
    # 'process-job-closed-task': {
    #     'task': 'job.tasks.check_zoho_closed_jobs',
    #     'schedule': crontab(),  # Runs every minute
    #     #  'schedule': crontab(minute=0, hour='*'),
    #     # 'schedule': crontab(minute=0, hour=0),  # every day at midnight
    # },
}


    
