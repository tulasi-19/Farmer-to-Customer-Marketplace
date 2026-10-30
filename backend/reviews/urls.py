from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('reviews', views.ReviewViewSet, basename='review')

urlpatterns = [
    path('reviews/eligibility/', views.ReviewEligibilityView.as_view(), name='review-eligibility'),
    path('admin/reviews/', views.AdminReviewListView.as_view(), name='admin-reviews'),
    path('admin/reviews/<int:pk>/', views.AdminReviewModerateView.as_view(), name='admin-review-moderate'),
] + router.urls
