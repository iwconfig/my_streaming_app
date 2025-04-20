from abc import ABC, abstractmethod
import logging
import shutil
import os

log = logging.getLogger(__name__)

class UploaderError(Exception):
    """Custom exception for uploader errors."""
    pass

class UploaderBase(ABC):
    """Abstract base class for uploader plugins."""

    def __init__(self, config):
        """
        Initialize the uploader.
        Args:
            config: The Flask app's configuration object.
        """
        self.config = config
        log.debug(f"Initialized uploader: {self.__class__.__name__}")

    @abstractmethod
    def upload(self, source_dir: str, user_id: int, track_id: int) -> tuple[str, str]:
        """
        Handles the storage of processed files and returns the final manifest URL.

        Args:
            source_dir: Path where FFmpeg output (segments + manifest) is located.
            user_id: ID of the user owning the track.
            track_id: ID of the track being processed.

        Returns:
            A tuple containing:
                - manifest_url (str): The publicly accessible URL for the manifest file.
                - manifest_type (str): 'HLS' or 'DASH' (usually determined by file extension).

        Raises:
            UploaderError: If the upload/storage process fails.
            FileNotFoundError: If expected manifest file is missing in source_dir.
        """
        pass

    def cleanup_source(self, source_dir: str):
        """
        Removes the temporary source directory created by FFmpeg.
        Called by the Celery task *after* successful upload.

        Args:
            source_dir: The directory path to remove.
        """
        if os.path.isdir(source_dir):
            try:
                log.info(f"Cleaning up temporary processing directory: {source_dir}")
                shutil.rmtree(source_dir)
            except OSError as e:
                 log.error(f"Error cleaning up source directory {source_dir}: {e}")
                 # Log error but don't raise - cleanup failure shouldn't fail the task usually
        else:
            log.warning(f"Cleanup requested, but source directory not found: {source_dir}")
