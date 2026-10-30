from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('products', views.ProductViewSet, basename='product')

urlpatterns = [
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('admin/products/', views.AdminProductListView.as_view(), name='admin-products'),
    path('admin/products/<int:pk>/', views.AdminProductToggleView.as_view(), name='admin-product-toggle'),
] + router.urls
