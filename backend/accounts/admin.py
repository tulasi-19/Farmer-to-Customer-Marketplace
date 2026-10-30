from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class FarmBridgeUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'phone', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('FarmBridge Profile', {'fields': ('role', 'phone', 'address', 'is_verified')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'role')}),
    )
