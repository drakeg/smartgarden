from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views as project_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", project_views.health, name="health"),
    path("", include("gardens.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

