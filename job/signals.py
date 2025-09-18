from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

@receiver(post_save)
def update_wordpress_on_form_change(sender, instance, created, **kwargs):
    """
    Automatically update WordPress when a JobOnboardingForm is updated
    """
    if sender.__name__ == 'JobOnboardingForm' and not created:
        JobTemplate = apps.get_model('job', 'JobTemplate')
        

        job_template = JobTemplate.objects.filter(
            job_onboarding=instance
        ).order_by('-created_at').first()
        
        if job_template:
            from .views import run_job_template_generation
            run_job_template_generation(instance, is_update=True)






from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from django.apps import apps

@receiver(pre_delete, sender='job.JobTemplate')
def delete_wordpress_post_on_job_delete(sender, instance, **kwargs):
    """
    Delete WordPress post when a JobTemplate is deleted
    """
    try:
        if instance.wp_page_id and hasattr(instance.user, 'wordpress_connection'):
            from .utility import delete_wordpress_post
            delete_wordpress_post(instance.user.wordpress_connection, instance.wp_page_id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting WordPress post on job delete: {str(e)}")