from django.utils import timezone
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
    gmb_post_limit = models.IntegerField(default=5)
    keyword_limit = models.IntegerField()
    seo_optimization_limit = models.IntegerField()
    job_post_limit = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=200, null=True, blank=True)

class OnboardingForm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name="onboardingform")
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
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    ctr = models.FloatField(default=0.0)
    average_position = models.FloatField(null=True, blank=True)
    last_updated = models.DateField(null=True, blank=True)

    @property
    def ctr(self):
        if self.impressions == 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)
    

class KeywordQuestion(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q: {self.question[:60]}"



class ServiceArea(models.Model):
    onboarding_form = models.ForeignKey(OnboardingForm, on_delete=models.CASCADE, related_name='service_areas')
    area_name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    posted_on = models.DateTimeField(auto_now_add=True)
    clicks = models.PositiveIntegerField(default=0)


class BusinessLocation(models.Model):
    onboarding_form = models.ForeignKey(OnboardingForm, on_delete=models.CASCADE, related_name='locations')
    location_name = models.CharField(max_length=1000)
    location_url = models.URLField(max_length=1000)


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

def default_month_year():
    return timezone.now().strftime('%Y-%m')

class SEOTask(models.Model):
    TASK_TYPES = (
        ('seo_optimization', 'SEO Optimization'),
        ('blog_writing', 'Blog Writing'),
        ('keyword_optimization', 'Keyword Optimization'),
        ('gmb_post', 'Google My Business Post')
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seo_tasks')
    service_page = models.ForeignKey(ServicePage, on_delete=models.CASCADE, null=True,blank=True, related_name='seo_tasks')
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ai_request_payload = models.JSONField(null=True, blank=True)
    ai_response_payload = models.JSONField(null=True, blank=True)
    optimized_content = models.TextField(null=True,blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    count_this_month = models.IntegerField(default=0)
    month_year = models.CharField(max_length=7, default=default_month_year)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    wp_page_url = models.URLField(null=True, blank=True)  # Store the final serice page WordPress URL
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    last_metrics_update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_task_type_display()} - {self.status} - {self.is_active}"

class Blog(models.Model):
    seo_task = models.ForeignKey(SEOTask, on_delete=models.CASCADE, related_name='blog')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, null=True)
    content = models.TextField()  # This will be the generated_content
    category = models.CharField(max_length=100, null=True, blank=True)  # Optional
    wp_post_id = models.IntegerField(null=True, blank=True) 
    wp_post_url = models.URLField(max_length=500, null=True, blank=True)

    wp_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=[
            ("draft", "Draft"),
            ("publish", "Published"),
            ("pending", "Pending Review"),
            ("future", "Scheduled"),
            ("private", "Private"),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BlogImage(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.blog.title}"
    

class GMBPost(models.Model):
    seo_task = models.ForeignKey(SEOTask, on_delete=models.CASCADE, related_name='gmb_post')
    content = models.TextField()
    area = models.CharField(max_length=200)
    keywords = models.JSONField(default=list)
    research_words = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GMB Post for {self.area} - {self.created_at}"
    


# In models.py
# models.py
class DataForSEOKeywordData(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='dataforseo_data')
    search_volume = models.PositiveIntegerField(default=0)
    competition = models.FloatField(null=True, blank=True)  # 0-1 scale
    competition_index = models.IntegerField(null=True, blank=True)  # 0-100 scale
    competition_level = models.CharField(max_length=20, null=True, blank=True)  # LOW, MEDIUM, HIGH
    cpc = models.FloatField(null=True, blank=True)  # Cost per click
    low_bid = models.FloatField(null=True, blank=True)
    high_bid = models.FloatField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('keyword',)
    
    def __str__(self):
        return f"{self.keyword.keyword} - {self.search_volume} searches"