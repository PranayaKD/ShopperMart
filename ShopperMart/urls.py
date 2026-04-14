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

handler404 = 'ShopperMartapp.views.catalog.error_404_view'
handler500 = 'ShopperMartapp.views.catalog.error_500_view'

from django.urls import re_path
from django.views.static import serve

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Serve media files in production for the free tier Render portfolio
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]