from django.urls import path

from . import views

urlpatterns = [
    path('farms/', views.FarmListView.as_view(), name='farm-list'),
    path('farms/<int:pk>/', views.FarmDetailView.as_view(), name='farm-detail'),

    path('farmer/profile/', views.FarmerProfileView.as_view(), name='farmer-profile'),
    path('farmer/kyc/', views.FarmerKYCView.as_view(), name='farmer-kyc'),
    path('farmer/kyc/<int:pk>/document/', views.KYCDocumentView.as_view(), name='farmer-kyc-document'),

    path('admin/kyc-applications/', views.AdminKYCListView.as_view(), name='admin-kyc-list'),
    path('admin/kyc-applications/<int:pk>/', views.AdminKYCDetailView.as_view(), name='admin-kyc-detail'),
    path('admin/kyc-applications/<int:pk>/document/', views.KYCDocumentView.as_view(), name='admin-kyc-document'),
    path('admin/kyc-applications/<int:pk>/approve/', views.AdminKYCApproveView.as_view(), name='admin-kyc-approve'),
    path('admin/kyc-applications/<int:pk>/reject/', views.AdminKYCRejectView.as_view(), name='admin-kyc-reject'),
]
