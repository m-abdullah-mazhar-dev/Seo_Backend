from django.contrib import admin

# Register your models here.
from django.contrib.auth import get_user_model
User = get_user_model()

# ------------------ User Admin ------------------ #
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone_number', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
