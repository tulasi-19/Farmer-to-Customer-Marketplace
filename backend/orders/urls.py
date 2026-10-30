from django.urls import path

from . import views

urlpatterns = [
    # customer
    path('orders/checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/cancel/', views.OrderCancelView.as_view(), name='order-cancel'),

    # farmer
    path('farmer/dashboard/', views.FarmerDashboardView.as_view(), name='farmer-dashboard'),
    path('farmer/shipments/', views.FarmerShipmentListView.as_view(), name='farmer-shipments'),
    path('farmer/shipments/<int:pk>/', views.FarmerShipmentDetailView.as_view(), name='farmer-shipment-detail'),
    path('farmer/shipments/<int:pk>/status/', views.FarmerShipmentStatusView.as_view(), name='farmer-shipment-status'),

    # admin
    path('admin/orders/', views.AdminOrderListView.as_view(), name='admin-orders'),
    path('admin/orders/<int:pk>/', views.AdminOrderDetailView.as_view(), name='admin-order-detail'),
    path('admin/orders/<int:pk>/mark-cod-paid/', views.AdminMarkCODPaidView.as_view(), name='admin-mark-cod-paid'),
    path('admin/shipments/<int:pk>/status/', views.AdminShipmentStatusView.as_view(), name='admin-shipment-status'),
]
