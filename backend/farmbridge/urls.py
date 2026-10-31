from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework_simplejwt.views import TokenRefreshView

# All API routes live under /api/v1/ so the contract can evolve (v2) safely.
api_v1 = [
    path('auth/', include('accounts.urls')),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('accounts.admin_urls')),
    path('', include('farms.urls')),
    path('', include('products.urls')),
    path('', include('cart.urls')),
    path('', include('orders.urls')),
    path('', include('reviews.urls')),
    path('ai/', include('ml_engine.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(api_v1)),
]

# Public media (product images, farm photos). KYC documents are NOT here - they live in
# private_media/ and are only streamed by a permission-checked API view.
# NOTE: Django's `serve` is fine for a demo; for real traffic use object storage (Cloudinary/S3).
urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]