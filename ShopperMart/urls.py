# ShopperMart/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import JsonResponse
from django.db import connection
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from ShopperMartapp.views import payments

def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
        db_status = "healthy" if row and row[0] == 1 else "unhealthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    is_healthy = db_status == "healthy"
    return JsonResponse({
        "status": "ok" if is_healthy else "degraded",
        "database": db_status,
        "engine": connection.vendor,
    }, status=200 if is_healthy else 503)

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=True)),
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    
    # OpenAPI 3.0 Documentation & Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    # REST API routes (v1 + default alias)
    path("api/create-order", payments.create_order, name="api-create-order-root"),
    path("api/create-order/", payments.create_order, name="api-create-order-root-slash"),
    path("api/verify-payment", payments.verify_payment, name="api-verify-payment-root"),
    path("api/verify-payment/", payments.verify_payment, name="api-verify-payment-root-slash"),
    path("api/v1/", include("ShopperMartapp.api_urls")),
    path("api/", include("ShopperMartapp.api_urls")),
    
    # Frontend application routes
    path("", include("ShopperMartapp.urls")),
]

handler404 = 'ShopperMartapp.views.catalog.error_404_view'
handler500 = 'ShopperMartapp.views.catalog.error_500_view'

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Serve media files in production for the free tier Render portfolio
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
