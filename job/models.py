from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
import uuid
from seo_services.models import WordPressConnection
User = get_user_model()
from django.core.exceptions import ValidationError
from django.utils import timezone

# Create your models here.

class JobOnboardingForm(models.Model):

    # user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="jobonboardingform")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="jobonboardingforms")
    # -------------------- Basic Company Details -------------------- 
    company_name = models.CharField(max_length=255)
    company_website = models.URLField(blank=True, null=True)
    company_address = models.TextField()
    drivers_weekly_earning = models.CharField(max_length=100,null=True,blank=True)
    drivers_weekly_miles = models.CharField(max_length=100,null=True,blank=True)
    cpm = models.CharField(max_length=100,null=True,blank=True)
    driver_percentage = models.CharField(max_length=100, help_text="If applicable", null=True, blank=True)
    truck_make_year = models.CharField(max_length=255)
    hauling_equipment = models.TextField()

    # -------------------- Vehicle Details --------------------
    transmission_automatic = models.BooleanField(default=False)
    transmission_manual = models.BooleanField(default=False)
    pay_type = models.CharField(max_length=50,null=True,blank=True)

    position_1099 = models.BooleanField(default=False)
    position_w2 = models.BooleanField(default=False)

    primary_running_areas = models.TextField()
    dedicated_lanes = models.TextField(blank=True, null=True)

    offer_cash_advances = models.BooleanField(default=False)
    cash_advance_amount = models.CharField(max_length=100, blank=True, null=True)

    referral_bonus = models.BooleanField(default=False)
    referral_bonus_amount = models.CharField(max_length=100, blank=True, null=True)

    fuel_card = models.BooleanField(default=False)
    fuel_card_type = models.CharField(max_length=255, blank=True, null=True)

    detention_layover_pay = models.CharField(max_length=100, blank=True, null=True)
    allow_pets_pessenger = models.BooleanField(default=False)

    # -------------------- Driver Benefits --------------------
    benefit_weekly_deposits = models.BooleanField(default=False)
    benefit_all_miles_paid = models.BooleanField(default=False)
    benefit_eco_bonus = models.BooleanField(default=False)
    benefit_pet_policy = models.BooleanField(default=False)
    benefit_rider_policy = models.BooleanField(default=False)
    benefit_gated_parking = models.BooleanField(default=False)
    benefit_eld_compliant = models.BooleanField(default=False)
    benefit_eld_support = models.BooleanField(default=False)
    benefit_dispatch_support = models.BooleanField(default=False)

    truck_governed_speed = models.CharField(max_length=100, blank=True, null=True)
    toll_passes = models.CharField(max_length=255, blank=True, null=True)

    # -------------------- Truck Equipment --------------------
    equip_fridge = models.BooleanField(default=False)
    equip_inverter = models.BooleanField(default=False)
    equip_microwave = models.BooleanField(default=False)
    equip_led = models.BooleanField(default=False)
    equip_apu = models.BooleanField(default=False)
    equip_disc_brakes = models.BooleanField(default=False)
    equip_no_inward_cam = models.BooleanField(default=False)
    equip_partial_equipment = models.BooleanField(default=False)

    # -------------------- Company Logo & Info --------------------
    company_logo = models.FileField(upload_to="logos/", blank=True, null=True)
    mc_dot_number = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=50)
    hiring_email = models.EmailField()

    terminal = models.CharField(max_length=255)
    governed_speed_detail = models.CharField(max_length=255)
    truck_make_year = models.CharField(max_length=255)

    # -------------------- CDL Requirements --------------------
    CDL_EXPERIENCE_CHOICES = [
        ("3", "3 Months"),
        ("6", "6 Months"),
        ("12", "1 Year"),
        ("18", "1.5 Years"),
        ("24", "2 Years"),
        ("36", "3+ Years"),
    ]
    cdl_experience_required = models.CharField(max_length=10, choices=CDL_EXPERIENCE_CHOICES)

    HIRING_AGE_CHOICES = [
        ("21", "21"),
        ("23", "23"),
        ("custom", "Custom"),
    ]
    minimum_hiring_age = models.CharField(max_length=20, choices=HIRING_AGE_CHOICES)
    hiring_age_custom = models.CharField(max_length=100, blank=True, null=True)

    disqualify_sap_dui_dwi = models.BooleanField(default=False)
    # clean_clearinghouse = models.CharField(max_length=255)
    # clean_drug_test = models.CharField(max_length=255)
    clean_clearinghouse = models.BooleanField(default=False)
    clean_drug_test = models.BooleanField(default=False)

    # -------------------- Driver Benefits Main --------------------
    main_weekly_deposits = models.BooleanField(default=False)
    main_safety_bonus = models.BooleanField(default=False)
    main_referral_bonus = models.BooleanField(default=False)
    main_dispatch_support = models.BooleanField(default=False)

    # -------------------- Equipment Main --------------------
    main_auto_transmission = models.BooleanField(default=False)
    main_manual_transmission = models.BooleanField(default=False)
    main_equip_fridge = models.BooleanField(default=False)
    main_equip_inverter = models.BooleanField(default=False)
    main_equip_microwave = models.BooleanField(default=False)
    main_equip_led = models.BooleanField(default=False)

    # -------------------- Travel Main --------------------
    travel_provided = models.BooleanField(default=False)
    travel_description = models.TextField(blank=True, null=True)

    # -------------------- Extras Main --------------------
    escrow_required = models.BooleanField(default=False)
    escrow_description = models.TextField(blank=True, null=True)

    repair_shop_onsite = models.BooleanField(default=False)
    gated_vehicle_parking = models.BooleanField(default=False)

    radius = models.CharField(max_length=100,null= True, blank=True )
    states = models.JSONField(default=list, null=True, blank=True)

    route = models.CharField(max_length=50, null= True, blank= True)
    position = models.CharField(max_length=50, null= True, blank=True)

    home_time = models.JSONField(default=list, blank=True)

    earning_type = models.CharField(max_length=50, null=True, blank= True)

        # -------------------- Cost Structure --------------------
    company_service_fee = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Percent for Owner Operator only"
    )
    service_fee_includes = models.JSONField(default=list, null=True, blank=True)

    trailer_rent = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    rent_trailers_to_drivers = models.BooleanField(null=True, blank=True)

    insurance_physical_damage = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    insurance_liability_cargo = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    ifta_fee = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    tablet_cost = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="Either number or 'driver'"
    )
    driver_provided_tablet = models.BooleanField(default=False)

    # Lease-specific
    truck_lease_weekly = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    down_payment = models.BooleanField(null=True, blank=True)
    down_payment_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    tolls_fuel = models.CharField(max_length=50,null=True, blank=True)

    def __str__(self):
        return self.company_name
    
class JobPage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_pages')
    wordpress_connection = models.ForeignKey(WordPressConnection, on_delete=models.CASCADE, related_name='job_pages')
    page_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.page_url
    
def default_month_year():
    return timezone.now().strftime('%Y-%m')

class JobTask(models.Model):
    TASK_TYPES = (
        ('job_blog_writing', 'Job Blog Writing'),
        ('job_template_generation', 'Job Posting Task'),
        ('job_gmb_post', 'Job GMB Post'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_tasks')
    job_onboarding = models.ForeignKey('JobOnboardingForm', on_delete=models.CASCADE, null=True, blank=True)
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ai_request_payload = models.JSONField(null=True, blank=True)
    ai_response_payload = models.JSONField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    count_this_month = models.IntegerField(default=0)
    month_year = models.CharField(max_length=7, default=default_month_year)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    wp_page_url = models.URLField(blank=True, null=True) # URL of the published job page
    published_date = models.DateTimeField(blank=True, null=True)
    # Metrics fields
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    ctr = models.FloatField(default=0)
    last_metrics_update = models.DateTimeField(blank=True, null=True)

    ga4_page_views = models.IntegerField(default=0)
    ga4_avg_time_on_page = models.FloatField(default=0)
    ga4_bounce_rate = models.FloatField(default=0)
    ga4_last_updated = models.DateTimeField(blank=True, null=True)


    def __str__(self):
        return f"{self.user.email} - {self.get_task_type_display()} - {self.status}"
    


class JobBlog(models.Model):
    job_task = models.OneToOneField('JobTask', on_delete=models.CASCADE, related_name='blog')
    title = models.CharField(max_length=255)
    content = models.TextField()
    wp_post_id = models.CharField(max_length=100, null=True, blank=True)
    wp_post_url = models.URLField(max_length=500, null=True, blank=True)

    published_date = models.DateTimeField(blank=True, null=True)

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

    # Metrics fields (to be populated by our new API)
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    ctr = models.FloatField(default=0)
    last_metrics_update = models.DateTimeField(blank=True, null=True)

    ga4_page_views = models.IntegerField(default=0)
    ga4_avg_time_on_page = models.FloatField(default=0) # in seconds
    ga4_bounce_rate = models.FloatField(default=0) # stored as a decimal (e.g., 0.55 for 55%)
    ga4_last_updated = models.DateTimeField(blank=True, null=True)


class JobBlogImage(models.Model):
    job_blog = models.ForeignKey(JobBlog, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.job_blog.title}"
    

class JobBlogKeyword(models.Model):
    job_blog = models.ForeignKey(JobBlog, on_delete=models.CASCADE, related_name='keywords')
    keyword = models.CharField(max_length=200)
    # Search Console Metrics
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    ctr = models.FloatField(default=0)
    average_position = models.FloatField(default=0)
    last_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('job_blog', 'keyword')  # Prevent duplicate keywords per blog

    def __str__(self):
        return f"{self.keyword} (for: {self.job_blog.title})"

class CRMType(models.Model):
    CRM_PROVIDERS = [
        ('hubspot', 'HubSpot'),
        ('pipedrive', 'Pipedrive'),
        ('zoho', 'Zoho CRM'),
        ('salesforce', 'Salesforce'),
        ('jobber', 'Jobber CRM'),
        ('zendesk', 'Zendesk CRM'),
    ]
    
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=20, choices=CRM_PROVIDERS)
    auth_type = models.CharField(max_length=10, choices=[
        ('oauth', 'OAuth'),
        ('api_key', 'API Key'),
        ('both', 'Both')
    ])
    oauth_client_id = models.CharField(max_length=255, blank=True, null=True)
    oauth_client_secret = models.CharField(max_length=255, blank=True, null=True)
    oauth_authorize_url = models.URLField(blank=True, null=True)
    oauth_token_url = models.URLField(blank=True, null=True)
    api_key_help_text = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Set default URLs based on provider
        if not self.oauth_authorize_url:
            if self.provider == 'hubspot':
                self.oauth_authorize_url = 'https://app.hubspot.com/oauth/authorize'
            elif self.provider == 'zoho':
                self.oauth_authorize_url = 'https://accounts.zoho.com/oauth/v2/auth'
            elif self.provider == 'jobber':
                self.oauth_authorize_url = 'https://api.getjobber.com/oauth/authorize'
            elif self.provider == 'zendesk':
                self.oauth_authorize_url = 'https://{subdomain}.zendesk.com/oauth/authorizations/new'
                
        if not self.oauth_token_url:
            if self.provider == 'hubspot':
                self.oauth_token_url = 'https://api.hubapi.com/oauth/v1/token'
            elif self.provider == 'zoho':
                self.oauth_token_url = 'https://accounts.zoho.com/oauth/v2/token'
            elif self.provider == 'jobber':
                self.oauth_token_url = 'https://api.getjobber.com/oauth/token'
            elif self.provider == 'zendesk':
                self.oauth_token_url = 'https://{subdomain}.zendesk.com/oauth/tokens'
                
        super().save(*args, **kwargs)

class CRMConnection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crm_connections')
    crm_type = models.ForeignKey(CRMType, on_delete=models.CASCADE)
    connection_name = models.CharField(max_length=100)
    
    # API Key authentication
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_domain = models.CharField(max_length=255, blank=True, null=True)  # For Pipedrive
    
    # OAuth authentication
    oauth_access_token = models.CharField(max_length=500, blank=True, null=True)
    oauth_refresh_token = models.CharField(max_length=500, blank=True, null=True)
    oauth_token_expiry = models.DateTimeField(blank=True, null=True)
    
    # Webhook details
    webhook_secret_token = models.UUIDField(default=uuid.uuid4, unique=True)
    webhook_url = models.URLField(blank=True, null=True)
    
    # Connection status
    is_connected = models.BooleanField(default=False)
    last_sync = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    processed_deals = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        if self.crm_type.auth_type in ['api_key', 'both'] and not self.api_key:
            raise ValidationError("API key is required for this CRM type")
        
        if self.crm_type.auth_type in ['oauth', 'both'] and not self.oauth_access_token:
            raise ValidationError("OAuth access token is required for this CRM type")
    
    def save(self, *args, **kwargs):
        if not self.webhook_url:
            self.webhook_url = f"https://abdullahmazhar-dev.app.n8n.cloud/webhook/job-closed/{self.webhook_secret_token}"
        super().save(*args, **kwargs)
    
    def is_token_expired(self):
        if self.oauth_token_expiry:
            return timezone.now() > self.oauth_token_expiry
        return False
    
    def __str__(self):
        return f"{self.user.first_name} - {self.crm_type.name}"

#
class ClientFeedback(models.Model):
    email = models.EmailField()
    job_id = models.CharField(max_length=100)
    service_area = models.CharField(max_length=200)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_satisfied = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    crm_connection = models.ForeignKey(CRMConnection, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True) 



# models.py
class OAuthState(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.CharField(max_length=100, unique=True)
    crm_type_id = models.IntegerField()
    redirect_uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)
    


# models.py
from django.db import models
from django.utils.text import slugify

class JobTemplate(models.Model):
    """
    Stores AI-generated job templates and WordPress integration details
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_templates")
    job_onboarding = models.ForeignKey(JobOnboardingForm, on_delete=models.CASCADE, related_name="templates")
    
    # AI Response Data
    ai_request_payload = models.JSONField(default=dict, null=True, blank=True)
    ai_response_payload = models.JSONField(default=dict, null=True, blank=True)
    generated_content = models.TextField(blank=True, null=True)
    
    # WordPress Integration
    wp_page_id = models.IntegerField(null=True, blank=True)
    wp_page_url = models.URLField(blank=True, null=True)
    wp_page_slug = models.SlugField(max_length=200, blank=True, null=True)
    wp_post_data = models.JSONField(default=dict, null=True, blank=True)
    
    # Status and Timestamps
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    published_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.job_onboarding.company_name} - {self.status}"
    
    def save(self, *args, **kwargs):
        if self.wp_page_url and not self.wp_page_slug:
            # Extract slug from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(self.wp_page_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if path_parts:
                self.wp_page_slug = path_parts[-1]
        super().save(*args, **kwargs)


# models.py
class FeedbackFormResponse(models.Model):
    SATISFACTION_CHOICES = [
        ('very_dissatisfied', 'Very Dissatisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('neutral', 'Neutral'),
        ('satisfied', 'Satisfied'),
        ('very_satisfied', 'Very Satisfied'),
    ]
    
    feedback = models.ForeignKey(ClientFeedback, on_delete=models.CASCADE, related_name='form_responses')
    satisfaction_level = models.CharField(max_length=20, choices=SATISFACTION_CHOICES)
    issues_faced = models.TextField(blank=True, null=True)
    suggestions = models.TextField(blank=True, null=True)
    would_recommend = models.BooleanField(null=True)
    contact_permission = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_satisfaction_level_display(self):
        """Get human-readable satisfaction level"""
        return dict(self.SATISFACTION_CHOICES).get(self.satisfaction_level, self.satisfaction_level)
    
    def __str__(self):
        return f"Feedback from {self.feedback.email} - {self.satisfaction_level}"