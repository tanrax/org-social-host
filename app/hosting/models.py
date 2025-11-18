"""
Models for Org Social Host application.
"""

from django.db import models
from django.utils import timezone


class HostedFile(models.Model):
    """Model to store hosted social.org files."""

    # User identification
    nickname = models.CharField(max_length=100, unique=True, db_index=True)

    # Virtual file token (for authentication)
    vfile_token = models.CharField(max_length=255, unique=True, db_index=True)
    vfile_timestamp = models.BigIntegerField()
    vfile_signature = models.CharField(max_length=255)

    # File storage
    file_content = models.TextField(default="")  # Content of the social.org file

    # Redirection (for migration)
    redirect_url = models.URLField(max_length=500, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_access = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "hosted_files"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nickname} ({self.vfile_token[:20]}...)"

    @property
    def public_url(self):
        """Return the public URL for this file."""
        from django.conf import settings

        return f"http://{settings.SITE_DOMAIN}/{self.nickname}/social.org"

    @property
    def is_redirected(self):
        """Check if this file is currently redirected."""
        return bool(self.redirect_url)

    def touch(self):
        """Update last_access timestamp."""
        self.last_access = timezone.now()
        self.save(update_fields=["last_access"])
