from django.db import models
from authentication.models import User

# Create your models here.

class Package(models.Model):
    name = models.CharField(max_length=100)
    interval = models.IntegerField(help_text="Task repeat interval in days")
    service_limit = models.IntegerField()
    service_area_limit = models.IntegerField()
    business_location_limit = models.IntegerField()
    blog_limit = models.IntegerField()
    keyword_limit = models.IntegerField()
    stripe_price_id = models.CharField(max_length=200, null=True, blank=True)

class OnboardingForm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    email = models.EmailField()
    about_business = models.TextField()
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True)


class Service(models.Model):
    onboarding_form = models.ForeignKey(OnboardingForm, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=200)
    rank_check = models.BooleanField(default=False)


class Keyword(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='keywords')
    keyword = models.CharField(max_length=100)


class ServiceArea(models.Model):
    onboarding_form = models.ForeignKey(OnboardingForm, on_delete=models.CASCADE, related_name='service_areas')
    area_name = models.CharField(max_length=200)


class BusinessLocation(models.Model):
    onboarding_form = models.ForeignKey(OnboardingForm, on_delete=models.CASCADE, related_name='locations')
    location_name = models.CharField(max_length=200)
    location_url = models.URLField()


class WordPressConnection(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wordpress_connection')
    site_url = models.URLField()
    access_token = models.CharField(max_length=500)  # For WordPress API
    username = models.CharField(max_length=255)  # ✅ Store username
    app_password = models.CharField(max_length=255)
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.site_url


class ServicePage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_pages')
    wordpress_connection = models.ForeignKey(WordPressConnection, on_delete=models.CASCADE, related_name='service_pages')
    page_url = models.URLField()
    blog_required = models.BooleanField(default=False)  # Tick for blog generation
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.page_url


class SEOTask(models.Model):
    TASK_TYPES = (
        ('seo_optimization', 'SEO Optimization'),
        ('blog_writing', 'Blog Writing'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seo_tasks')
    service_page = models.ForeignKey(ServicePage, on_delete=models.CASCADE, related_name='seo_tasks')
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ai_request_payload = models.JSONField(null=True, blank=True)
    ai_response_payload = models.JSONField(null=True, blank=True)
    optimized_content = models.TextField(null=True,blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_task_type_display()} - {self.status}"


class Blog(models.Model):
    seo_task = models.OneToOneField(SEOTask, on_delete=models.CASCADE, related_name='blog')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, null=True)
    content = models.TextField()  # This will be the generated_content
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BlogImage(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.blog.title}"
