from django.contrib import admin

from .models import Farm, KYCApplication


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['farm_name', 'user', 'district', 'state', 'kyc_status', 'created_at']
    list_filter = ['kyc_status', 'state']
    search_fields = ['farm_name', 'user__username']


@admin.register(KYCApplication)
class KYCApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'farm', 'id_type', 'status', 'reviewed_by', 'submitted_at']
    list_filter = ['status', 'id_type']
    # Decisions go through the API (approve/reject with a reason) so the
    # farm's cached status can never get out of sync with the application.
    readonly_fields = [f.name for f in KYCApplication._meta.fields]

    def has_add_permission(self, request):
        return False
