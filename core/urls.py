"""
URL configuration for Org Social Host project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from app.hosting import views

urlpatterns = [
    # Root endpoint
    path("", views.root_view, name="root"),
    # Hosting endpoints
    path("", include("app.hosting.urls")),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
