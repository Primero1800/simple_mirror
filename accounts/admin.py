from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import OTPCode, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin view for the custom email-based User model."""

    ordering = ("email",)
    list_display = ("email", "is_active", "is_staff", "is_superuser", "date_joined")
    list_display_links = ("email",)
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email",)
    date_hierarchy = "date_joined"
    list_per_page = 25
    actions_on_top = True
    actions_on_bottom = False

    fieldsets = (
        (None, {"fields": ("email", "password"), "classes": ("wide",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined"), "classes": ("wide",)},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """Admin view for OTP codes — read-only inspection tool."""

    list_display = ("user", "code", "created_at", "expires_at", "is_valid")
    list_display_links = ("user", "code")
    list_filter = ("created_at",)
    search_fields = ("user__email",)
    readonly_fields = ("user", "code", "created_at", "expires_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    actions_on_top = False
    actions_on_bottom = True

    def is_valid(self, obj: OTPCode) -> bool:
        return obj.is_valid()

    is_valid.boolean = True  # type: ignore[attr-defined]
    is_valid.short_description = "Valid"  # type: ignore[attr-defined]
