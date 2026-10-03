from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class DemoUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Demo profile", {"fields": ("display_name", "role")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Demo profile", {"fields": ("email", "role")}),)
