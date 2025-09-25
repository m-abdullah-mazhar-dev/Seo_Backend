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
        # 'schedule': crontab(minute='*/5'),
        'schedule': crontab(),  # Runs every minute
        'args': (),  # You can pass arguments if needed
    },
    'process-due-job-tasks-every-minute': {
        'task': 'seo_services.tasks.process_due_job_tasks',
        'schedule': crontab(), 
        # 'schedule': crontab(minute='*/5'),
        # 'args': (),  # You can pass arguments if needed
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
    'process-job-closed-task': {
        'task': 'job.tasks.check_zoho_closed_jobs',
        # 'schedule': crontab(),  # Runs every minute
         'schedule': crontab(minute=0, hour='*'),
        # 'schedule': crontab(minute=0, hour=0),  # every day at midnight
    },
        # HubSpot task (new)
    'check-hubspot-closed-jobs': {
        'task': 'job.tasks.check_hubspot_closed_jobs',
        # 'schedule': crontab(),  # Runs every minute
        'schedule': crontab(minute=30, hour='*/2'),  # Run 30 minutes after Zoho
        'options': {
            'expires': 7200,
        }
    },
    # Jobber task (new)
    'check-jobber-closed-jobs': {
        'task': 'job.tasks.check_jobber_closed_jobs',
        # 'schedule': crontab(),  # Runs every minute

        'schedule': crontab(minute=0, hour='*/3'),  # Run every 3 hours
        'options': {
            'expires': 10800,  # 3 hours
        }
    },
    'check-zendesk-solved-tickets': {
        'task': 'job.tasks.check_zendesk_solved_tickets',
        # 'schedule': crontab(),  # Runs every minute
        'schedule': crontab(minute=15, hour='*/3'), 
        'options': {
            'expires': 10800,  # 3 hours
        } # Example: every 4 hours at :15
    },
    # Salesforce task (new)
    'check-salesforce-closed-jobs': {
        'task': 'job.tasks.check_salesforce_closed_jobs',
        # 'schedule': crontab(),  # Runs every minute
        'schedule': crontab(minute=15, hour='*/4'),  # Run every 4 hours, 15 minutes offset
        'options': {
            'expires': 14400,  # 4 hours
        }
    },
    
}


    
