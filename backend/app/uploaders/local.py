import os
import shutil
import logging
from urllib.parse import urljoin # For creating URLs correctly
from .base import UploaderBase, UploaderError

log = logging.getLogger(__name__)

class LocalUploader(UploaderBase):
    """
    'Uploads' files by simply ensuring they are in the correct final
    local directory structure and calculating the corresponding URL based
    on configuration. Assumes an external webserver serves files from
    LOCAL_STORAGE_OUTPUT_DIR.
    """

    def upload(self, source_dir: str, user_id: int, track_id: int) -> tuple[str, str]:
        """
        Moves files to the final location if needed (though task writes there directly)
        and constructs the URL.

        Final structure is assumed: LOCAL_STORAGE_OUTPUT_DIR / user_id / track_id / [files]
        """
        log.info(f"Processing local storage for track {track_id} from source {source_dir}")

        final_base_dir = self.config.get('LOCAL_STORAGE_OUTPUT_DIR')
        base_url = self.config.get('LOCAL_STORAGE_URL_BASE')

        if not final_base_dir or not base_url:
            raise UploaderError("LOCAL_STORAGE_OUTPUT_DIR or LOCAL_STORAGE_URL_BASE not configured.")

        # --- The Celery task now writes directly to the final location ---
        # --- So we just need to find the manifest and build the URL ---
        # final_track_dir = os.path.join(final_base_dir, str(user_id), str(track_id))
        final_track_dir = source_dir # Task already wrote here based on current tasks.py

        manifest_hls = os.path.join(final_track_dir, "manifest.m3u8")
        manifest_dash = os.path.join(final_track_dir, "manifest.mpd") # If DASH is added later

        manifest_local_path = None
        manifest_relative_path = None
        manifest_type = None

        if os.path.exists(manifest_hls):
            manifest_local_path = manifest_hls
            # Relative path for URL construction: user_id/track_id/manifest.m3u8
            manifest_relative_path = os.path.join(str(user_id), str(track_id), "manifest.m3u8")
            manifest_type = "HLS"
            log.debug(f"Found HLS manifest: {manifest_local_path}")
        elif os.path.exists(manifest_dash):
             manifest_local_path = manifest_dash
             manifest_relative_path = os.path.join(str(user_id), str(track_id), "manifest.mpd")
             manifest_type = "DASH"
             log.debug(f"Found DASH manifest: {manifest_local_path}")
        else:
            log.error(f"No manifest file (manifest.m3u8 or manifest.mpd) found in {final_track_dir}")
            raise FileNotFoundError(f"Manifest file not found in output directory {final_track_dir}")

        # Construct the final public URL
        # Ensure base_url ends with '/' if using subdirectories
        if not base_url.endswith('/'):
             log.warning("LOCAL_STORAGE_URL_BASE should ideally end with '/' when using subdirectories.")
             base_url += '/'

        # urljoin handles combining base URL and relative path robustly
        final_manifest_url = urljoin(base_url, manifest_relative_path.replace(os.sep, '/')) # Ensure forward slashes for URL

        log.info(f"Calculated manifest URL for track {track_id}: {final_manifest_url}")

        # Optional: Verify segments exist?

        # The 'upload' is essentially just confirming the files are there and calculating the URL
        return final_manifest_url, manifest_type

    # Override cleanup_source if needed, but base implementation might suffice
    # def cleanup_source(self, source_dir: str):
    #     super().cleanup_source(source_dir) # Call base or implement specific logic
