"""
URL configuration for Org Social Host project.
"""

from django.urls import include, path

from app.hosting import views

urlpatterns = [
    # Root endpoint
    path("", views.root_view, name="root"),
    # Hosting endpoints
    path("", include("app.hosting.urls")),
]
