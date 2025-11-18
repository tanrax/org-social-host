"""
Background tasks for Org Social Host.
"""

import logging
import os
from datetime import timedelta
from pathlib import Path

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

    # Delete files from storage and database
    for hosted_file in stale_files:
        try:
            # Delete physical file
            file_path = Path(hosted_file.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {hosted_file.file_path}")

            # Delete parent directory if empty
            parent_dir = file_path.parent
            if parent_dir.exists() and not list(parent_dir.iterdir()):
                parent_dir.rmdir()
                logger.info(f"Deleted empty directory: {parent_dir}")

            # Delete database record
            nickname = hosted_file.nickname
            hosted_file.delete()
            logger.info(f"Deleted hosted file record: {nickname}")

        except Exception as e:
            logger.error(f"Error deleting file {hosted_file.nickname}: {e}")

    logger.info(f"Cleanup completed. Deleted {count} stale files.")
