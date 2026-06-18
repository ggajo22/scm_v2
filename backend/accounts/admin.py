from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import AdminUser


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    list_display = ("username", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
