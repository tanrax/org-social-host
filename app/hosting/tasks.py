"""
Background tasks for Org Social Host.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from .models import HostedFile

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(hour="0", minute="0"))
def cleanup_stale_files():
    """
    Clean up files that haven't been updated within the TTL period.
    Runs daily at midnight UTC.
    """
    logger.info("Starting cleanup of stale files...")

    # Calculate cutoff date
    cutoff_date = timezone.now() - timedelta(days=settings.FILE_TTL_DAYS)

    # Find stale files
    stale_files = HostedFile.objects.filter(last_access__lt=cutoff_date)
    count = stale_files.count()

    if count == 0:
        logger.info("No stale files found.")
        return

    logger.info(f"Found {count} stale files to delete.")

    # Delete database records
    for hosted_file in stale_files:
        try:
            nickname = hosted_file.nickname
            hosted_file.delete()
            logger.info(f"Deleted hosted file record: {nickname}")

        except Exception as e:
            logger.error(f"Error deleting file {hosted_file.nickname}: {e}")

    logger.info(f"Cleanup completed. Deleted {count} stale files.")
