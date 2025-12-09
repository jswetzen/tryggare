from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminUser


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    model = AdminUser
    list_display = ("username", "name", "is_staff", "is_active", "last_login")
    list_filter = ("is_staff", "is_active")
    ordering = ("username",)
    search_fields = ("username", "name")

    fieldsets = (
        (None, {"fields": ("username", "password", "name")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "name",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
