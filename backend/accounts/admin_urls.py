from django.urls import path

from . import admin_views

urlpatterns = [
    path('admin/stats/', admin_views.AdminStatsView.as_view(), name='admin-stats'),
    path('admin/users/', admin_views.AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', admin_views.AdminUserDetailView.as_view(), name='admin-user-detail'),
]
