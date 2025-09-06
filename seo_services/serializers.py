from bs4 import BeautifulSoup
from rest_framework import serializers

from payment.models import UserSubscription
from .models import *
from django.utils.html import strip_tags


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'
        read_only_fields = ['stripe_price_id']
        extra_kwargs = {
            'price': {'required': False},
        }


class KeywordSerialzier(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = ['id','keyword']

class ServiceSerializer(serializers.ModelSerializer):
    keywords = KeywordSerialzier(many = True)
    class Meta:
        model = Service
        fields = ['id', 'service_name', 'rank_check', 'keywords']

class ServiceAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        fields = ['id', 'area_name']

class BusinessLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessLocation
        fields = ['id', 'location_name', 'location_url']


class OnBoardingFormSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True)  # Nested services
    service_areas = ServiceAreaSerializer(many=True)  # Nested areas
    business_locations = BusinessLocationSerializer(many=True,source='locations')
    user = serializers.StringRelatedField(read_only=True)



    class Meta:
        model = OnboardingForm
        fields = [
            'id','user', 'company_name', 'phone_number', 'address', 'email', 'about_business', 'package',
            'services', 'service_areas', 'business_locations'
        ]


    def validate(self, attrs):
        package = attrs.get("package")
        services = self.initial_data.get("services", [])
        service_areas = self.initial_data.get("service_areas", [])
        business_locations = self.initial_data.get("business_locations", [])

        # 1️⃣ Check service limit
        if len(services) > package.service_limit:
            raise serializers.ValidationError({
                "services": f"Your package allows only {package.service_limit} services."
            })

        # 2️⃣ Check keyword limit per service
        # for idx, service in enumerate(services, start=1):
        #     keywords = service.get("keywords", [])
        #     if len(keywords) > package.keyword_limit:
        #         raise serializers.ValidationError({
        #             "services": f"Service {idx} exceeds keyword limit "
        #                         f"({len(keywords)}/{package.keyword_limit})."
        #         })

        # 3️⃣ Check service area limit
        if len(service_areas) > package.service_area_limit:
            raise serializers.ValidationError({
                "service_areas": f"Your package allows only {package.service_area_limit} service areas."
            })

        # 4️⃣ Check business location limit
        if len(business_locations) > package.business_location_limit:
            raise serializers.ValidationError({
                "business_locations": f"Your package allows only {package.business_location_limit} locations."
            })
        return attrs
    
    def create(self, validated_data):
        services_data = validated_data.pop('services')
        service_areas_data = validated_data.pop('service_areas')
        business_locations_data = validated_data.pop('locations')

        user = self.context['request'].user
        print(user, "---------------")

        onboarding_form = OnboardingForm.objects.create(user=user, **validated_data)

        for service_data in services_data:
            keywords_data = service_data.pop('keywords')
            service = Service.objects.create(onboarding_form=onboarding_form, **service_data)

            for keyword_data in keywords_data:
                Keyword.objects.create(service=service, **keyword_data)

        for service_area_data in service_areas_data:
            ServiceArea.objects.create(onboarding_form=onboarding_form, **service_area_data)

        for business_location_data in business_locations_data:
            BusinessLocation.objects.create(onboarding_form=onboarding_form, **business_location_data)

        return onboarding_form

    def update(self, instance, validated_data):
        # Update top-level fields
        for attr, value in validated_data.items():
            if attr not in ['services', 'service_areas', 'locations']:  # Skip nested fields
                setattr(instance, attr, value)
        instance.save()

        # Handle nested services and keywords
        if 'services' in validated_data:
            services_data = validated_data.pop('services')
            self._handle_services_update(instance, services_data)

        # Handle nested service areas
        if 'service_areas' in validated_data:
            service_areas_data = validated_data.pop('service_areas')
            self._handle_service_areas_update(instance, service_areas_data)

        # Handle nested business locations
        if 'locations' in validated_data:
            locations_data = validated_data.pop('locations')
            self._handle_locations_update(instance, locations_data)

        return instance

    def _handle_services_update(self, instance, services_data):
        existing_services = {service.id: service for service in instance.services.all()}
        kept_service_ids = []
        
        for service_data in services_data:
            service_id = service_data.get('id')
            
            if service_id and service_id in existing_services:
                # Update existing service
                service = existing_services[service_id]
                keywords_data = service_data.pop('keywords', [])
                
                for key, value in service_data.items():
                    setattr(service, key, value)
                service.save()
                
                # Handle keywords update
                self._update_keywords(service, keywords_data)
                kept_service_ids.append(service_id)
            else:
                # Create new service
                keywords_data = service_data.pop('keywords', [])
                new_service = Service.objects.create(onboarding_form=instance, **service_data)
                
                # Create new keywords
                for keyword_data in keywords_data:
                    Keyword.objects.create(service=new_service, **keyword_data)
                kept_service_ids.append(new_service.id)
        
        # Delete services not included in the update
        for service_id, service in existing_services.items():
            if service_id not in kept_service_ids:
                service.delete()

    def _handle_service_areas_update(self, instance, service_areas_data):
        existing_areas = {area.id: area for area in instance.service_areas.all()}
        kept_area_ids = []
        
        for area_data in service_areas_data:
            area_id = area_data.get('id')
            
            if area_id and area_id in existing_areas:
                # Update existing area
                area = existing_areas[area_id]
                for key, value in area_data.items():
                    setattr(area, key, value)
                area.save()
                kept_area_ids.append(area_id)
            else:
                # Create new area
                new_area = ServiceArea.objects.create(onboarding_form=instance, **area_data)
                kept_area_ids.append(new_area.id)
        
        # Delete areas not included in the update
        for area_id, area in existing_areas.items():
            if area_id not in kept_area_ids:
                area.delete()

    def _handle_locations_update(self, instance, locations_data):
        existing_locations = {loc.id: loc for loc in instance.locations.all()}
        kept_location_ids = []
        
        for location_data in locations_data:
            location_id = location_data.get('id')
            
            if location_id and location_id in existing_locations:
                # Update existing location
                location = existing_locations[location_id]
                for key, value in location_data.items():
                    setattr(location, key, value)
                location.save()
                kept_location_ids.append(location_id)
            else:
                # Create new location
                new_location = BusinessLocation.objects.create(onboarding_form=instance, **location_data)
                kept_location_ids.append(new_location.id)
        
        # Delete locations not included in the update
        for location_id, location in existing_locations.items():
            if location_id not in kept_location_ids:
                location.delete()

    def _update_keywords(self, service, keywords_data):
        existing_keywords = {keyword.id: keyword for keyword in service.keywords.all()}
        kept_keyword_ids = []
        
        for keyword_data in keywords_data:
            keyword_id = keyword_data.get('id')
            
            if keyword_id and keyword_id in existing_keywords:
                # Update existing keyword
                keyword = existing_keywords[keyword_id]
                for key, value in keyword_data.items():
                    setattr(keyword, key, value)
                keyword.save()
                kept_keyword_ids.append(keyword_id)
            else:
                # Create new keyword
                new_keyword = Keyword.objects.create(service=service, **keyword_data)
                kept_keyword_ids.append(new_keyword.id)
        
        # Delete keywords not included in the update
        for keyword_id, keyword in existing_keywords.items():
            if keyword_id not in kept_keyword_ids:
                keyword.delete()

class ServiceAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        fields = ['area_name', 'description', 'posted_on', 'clicks']


class KeywordSerializer(serializers.ModelSerializer):
    ctr = serializers.SerializerMethodField()

    class Meta:
        model = Keyword
        fields = ['keyword', 'clicks', 'impressions', 'ctr']

    def get_ctr(self, obj):
        return obj.ctr


class BlogSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    category = serializers.CharField(source="seo_task.task_type", read_only=True)
    description = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = ['id','wp_post_id' ,'wp_post_url','wp_status','title', 'content',  'description' ,'category', 'image']

    def get_image(self, obj):
        image = obj.images.first()
        return image.image_url if image else None

    def get_description(self, obj):
        plain_text = strip_tags(obj.content)  # remove <p>, <h1>, etc.
        return plain_text[:200] + "..." if plain_text else None


class BlogEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ['title', 'content', 'category']
        extra_kwargs = {
            'content': {'required': False},  # Make fields optional for partial updates
            'title': {'required': False},
            'category': {'required': False}
        }
    def validate_content(self, value):
        if value:
            try:
                soup = BeautifulSoup(value, 'html.parser')
                if not soup.find('html') or not soup.find('body'):
                    raise serializers.ValidationError("Content must be complete HTML document")
            except Exception as e:
                raise serializers.ValidationError(f"Invalid HTML content: {str(e)}")
        return value


# class AdminClientDetailSerializer(serializers.ModelSerializer):
#     full_name = serializers.SerializerMethodField()
#     gbp_status = serializers.SerializerMethodField()
#     wp_status = serializers.SerializerMethodField()
#     payment_status = serializers.SerializerMethodField()

#     blogs = serializers.SerializerMethodField()
#     onboarding = serializers.SerializerMethodField()

#     class Meta:
#         model = User
#         fields = [
#             'id', 'full_name', 'email', 'phone_number',
#             'gbp_status', 'wp_status', 'payment_status',
#             'blogs', 'onboarding'
#         ]

#     def get_full_name(self, obj):
#         return f"{obj.first_name} {obj.last_name}"

#     def get_gbp_status(self, obj):
#         return None  # No GBP yet

#     def get_wp_status(self, obj):
#         return "Connected" if hasattr(obj, 'wordpress_connection') else "Not Connected"

#     def get_payment_status(self, obj):
#         try:
#             return obj.usersubscription.status
#         except UserSubscription.DoesNotExist:
#             return "No Subscription"

#     def get_blogs(self, obj):
#         blogs = Blog.objects.filter(seo_task__user=obj, seo_task__task_type="blog_writing")
#         return BlogSerializer(blogs, many=True).data

#     def get_onboarding(self, obj):
#         onboarding = OnboardingForm.objects.filter(user=obj).first()
#         if onboarding:
#             return {
#                 "company_name": onboarding.company_name,
#                 "phone_number": onboarding.phone_number,
#                 "email": onboarding.email,
#                 "services": ServiceSerializer(onboarding.services.all(), many=True).data,
#                 "service_areas": ServiceAreaSerializer(onboarding.service_areas.all(), many=True).data,
#                 "business_locations": BusinessLocationSerializer(onboarding.locations.all(), many=True).data
#             }
#         return {}


from g_matrix.models import *
class AdminClientDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    gbp_status = serializers.SerializerMethodField()
    wp_status = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    search_console_status = serializers.SerializerMethodField()
    analytics_status = serializers.SerializerMethodField()

    blogs = serializers.SerializerMethodField()
    onboarding = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "full_name", "email", "phone_number",
            "gbp_status", "wp_status", "payment_status",
            "search_console_status", "analytics_status",
            "blogs", "onboarding"
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    # ✅ Google Business Profile (GBP)
    def get_gbp_status(self, obj):
        token = GoogleBusinessToken.objects.filter(user=obj).first()
        if not token:
            return "Not Connected"
        expiry = token.credentials.get("expiry") if token.credentials else None
        if expiry and timezone.now() >= timezone.datetime.fromisoformat(expiry):
            return "Expired"
        return "Connected"

    # ✅ WordPress
    def get_wp_status(self, obj):
        return "Connected" if hasattr(obj, "wordpress_connection") else "Not Connected"

    # ✅ Payment
    def get_payment_status(self, obj):
        try:
            return obj.usersubscription.status
        except UserSubscription.DoesNotExist:
            return "No Subscription"

    # ✅ Search Console
    def get_search_console_status(self, obj):
        token = SearchConsoleToken.objects.filter(user=obj).first()
        if not token:
            return "Not Connected"
        expiry = token.credentials.get("expiry") if token.credentials else None
        if expiry and timezone.now() >= timezone.datetime.fromisoformat(expiry):
            return "Expired"
        return "Connected"

    # ✅ Analytics
    def get_analytics_status(self, obj):
        token = GoogleAnalyticsToken.objects.filter(user=obj).first()
        if not token:
            return "Not Connected"
        if token.token_expiry and token.token_expiry <= timezone.now():
            return "Expired"
        return "Connected"

    # ✅ Blogs
    def get_blogs(self, obj):
        blogs = Blog.objects.filter(seo_task__user=obj, seo_task__task_type="blog_writing")
        return BlogSerializer(blogs, many=True).data

    # ✅ Onboarding
    def get_onboarding(self, obj):
        onboarding = OnboardingForm.objects.filter(user=obj).first()
        if onboarding:
            return {
                "company_name": onboarding.company_name,
                "phone_number": onboarding.phone_number,
                "email": onboarding.email,
                "services": ServiceSerializer(onboarding.services.all(), many=True).data,
                "service_areas": ServiceAreaSerializer(onboarding.service_areas.all(), many=True).data,
                "business_locations": BusinessLocationSerializer(onboarding.locations.all(), many=True).data,
            }
        return {}
    


class CompanyDetailsSerializer(serializers.ModelSerializer):
    package = PackageSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    service_areas = ServiceAreaSerializer(many=True, read_only=True)
    business_locations = BusinessLocationSerializer(many=True, source='locations', read_only=True)
    blogs = serializers.SerializerMethodField()
    gbp_status = serializers.SerializerMethodField()
    wp_status = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingForm
        fields = [
            'id', 'company_name', 'phone_number', 'address', 'email',
            'about_business', 'package', 'services', 'service_areas',
            'business_locations', 'blogs', 'gbp_status', 'wp_status', 'payment_status'
        ]

    def get_blogs(self, obj):
        blogs = Blog.objects.filter(seo_task__user=obj.user, seo_task__task_type="blog_writing")
        return BlogSerializer(blogs, many=True).data

    def get_gbp_status(self, obj):
        # Placeholder — replace with actual GBP connection check
        return "Connected" if hasattr(obj.user, 'google_business_profile') else "Not Connected"

    def get_wp_status(self, obj):
        return "Connected" if hasattr(obj.user, 'wordpress_connection') else "Not Connected"

    def get_payment_status(self, obj):
        try:
            return obj.user.usersubscription.status
        except UserSubscription.DoesNotExist:
            return "No Subscription"
