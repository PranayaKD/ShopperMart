# ShopperMart/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),          # 👈 Required for Social Logins
    path("api/v1/", include("ShopperMartapp.api_urls")),  # 👈 REST API routes
    path("", include("ShopperMartapp.urls")),             # 👈 Frontend app routes
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)