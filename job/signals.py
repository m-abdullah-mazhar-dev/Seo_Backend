# job/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

@receiver(post_save)
def update_wordpress_on_form_change(sender, instance, created, **kwargs):
    """
    Automatically update WordPress when a JobOnboardingForm is updated
    """
    # Check if the sender is JobOnboardingForm without importing it directly
    if sender.__name__ == 'JobOnboardingForm' and not created:
        # Use apps.get_model to avoid circular imports
        JobTemplate = apps.get_model('job', 'JobTemplate')
        
        # Find the latest job template for this form
        job_template = JobTemplate.objects.filter(
            job_onboarding=instance
        ).order_by('-created_at').first()
        
        if job_template:
            # Import the utility function here to avoid circular imports
            from .views import run_job_template_generation
            # Regenerate and update the WordPress post
            run_job_template_generation(instance, is_update=True)