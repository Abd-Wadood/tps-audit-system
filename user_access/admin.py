from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User

from .constants import ACCOUNTING_ROLE, REPORT_ROLE, STOCK_ROLE


ROLE_NAMES = [STOCK_ROLE, ACCOUNTING_ROLE, REPORT_ROLE]


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    list_display = ("name",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_superuser", "role_names")
    list_filter = BaseUserAdmin.list_filter + ("groups",)
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Workspace Access", {"fields": ("groups",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "first_name", "last_name", "password1", "password2", "is_staff", "is_superuser", "groups"),
            },
        ),
    )

    def role_names(self, obj):
        roles = list(obj.groups.filter(name__in=ROLE_NAMES).values_list("name", flat=True))
        if obj.is_superuser:
            return "Owner/Admin"
        return ", ".join(roles) if roles else "No workspace role"

    role_names.short_description = "Workspace Roles"

