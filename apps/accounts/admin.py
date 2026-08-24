from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Direction, RolePermission, User


@admin.register(User)
class RoseUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Rose", {"fields": ("role", "direction", "telephone")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "direction", "is_staff")
    list_filter = UserAdmin.list_filter + ("role", "direction")


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "autorise")
    list_filter = ("role", "autorise")
