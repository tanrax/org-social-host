"""
URL configuration for hosting app.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("signup", views.signup_view, name="signup"),
    path("upload", views.upload_view, name="upload"),
    path("delete", views.delete_view, name="delete"),
    path("redirect", views.redirect_view, name="redirect"),
    path("remove-redirect", views.remove_redirect_view, name="remove-redirect"),
    path("<str:nickname>/social.org", views.serve_file_view, name="serve-file"),
]
