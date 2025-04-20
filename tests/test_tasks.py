import pytest
import os
import subprocess
import shutil
from contextlib import ExitStack
from unittest.mock import patch, MagicMock, ANY

# Import task function directly for testing its .run method
from app.tasks import process_audio_task, get_audio_duration_ms
# Import models needed for checks and mocking spec
from app.models import Track, TrackStatus, ManifestType
# Import base class for mocking uploader interface
from app.uploaders.base import UploaderBase, UploaderError
# Import Celery exceptions for testing retry logic
from celery.exceptions import Retry, MaxRetriesExceededError

# --- Unit Tests for get_audio_duration_ms ---

@patch('subprocess.run')
def test_get_audio_duration_success_format(mock_run, app):
    mock_process = MagicMock()
    mock_process.stdout = '{"format": {"duration": "123.456"}}'
    mock_process.returncode = 0
    mock_run.return_value = mock_process
    with app.app_context():
        duration = get_audio_duration_ms("dummy.mp3")
    assert duration == 123456
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0][0] == app.config['FFPROBE_PATH']

@patch('subprocess.run')
def test_get_audio_duration_success_stream(mock_run, app):
    mock_process = MagicMock()
    mock_process.stdout = '{"format": {}, "streams": [{"codec_type": "audio", "duration": "60.1"}]}'
    mock_process.returncode = 0
    mock_run.return_value = mock_process
    with app.app_context():
         duration = get_audio_duration_ms("dummy.mp3")
    assert duration == 60100
    mock_run.assert_called_once()

@patch('subprocess.run')
def test_get_audio_duration_ffprobe_fail(mock_run, app):
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="FFprobe error")
    with app.app_context():
        duration = get_audio_duration_ms("dummy.mp3")
    assert duration is None
    mock_run.assert_called_once()

@patch('subprocess.run')
def test_get_audio_duration_no_duration(mock_run, app):
    mock_process = MagicMock()
    mock_process.stdout = '{"format": {}, "streams": [{"codec_type": "video"}]}'
    mock_process.returncode = 0
    mock_run.return_value = mock_process
    with app.app_context():
        duration = get_audio_duration_ms("dummy.mp3")
    assert duration is None
    mock_run.assert_called_once()


# --- Unit Tests for process_audio_task ---

@pytest.fixture
def mock_task_deps():
    """Fixture to mock dependencies used by process_audio_task."""
    mock_db_session = MagicMock()
    mock_track = MagicMock(spec=Track)
    mock_track.id = 1
    mock_track.user_id = 1
    mock_track.status = TrackStatus.PENDING
    mock_track.title = "User Title"
    mock_track.artist = None; mock_track.album = None; mock_track.track_number = None; mock_track.duration_ms = None
    mock_db_session.get.return_value = mock_track
    mock_subprocess_run = MagicMock()
    mock_uploader_instance = MagicMock(spec=UploaderBase)
    mock_uploader_instance.cleanup_source = MagicMock()
    mock_uploader_instance.upload.return_value = ("/mocked/url/manifest.m3u8", "HLS")
    mock_get_uploader = MagicMock(return_value=mock_uploader_instance)
    mock_os_makedirs = MagicMock()
    mock_os_path_exists = MagicMock(return_value=True)
    mock_os_remove = MagicMock()
    mock_shutil_rmtree_base = MagicMock()
    mock_task_retry = MagicMock() # Mock retry method

    # Also mock the metadata/duration helpers used within the task
    mock_extract_metadata = MagicMock(return_value={}) # Default: returns empty dict
    mock_get_duration_ffprobe = MagicMock(return_value=None) # Default: ffprobe finds nothing

    patches_dict = {
        'app.tasks.db.session': mock_db_session,
        'app.tasks.subprocess.run': mock_subprocess_run,
        'app.tasks.get_uploader_plugin': mock_get_uploader,
        'app.tasks.os.makedirs': mock_os_makedirs,
        'app.tasks.os.path.exists': mock_os_path_exists,
        'app.tasks.os.remove': mock_os_remove,
        'app.uploaders.base.shutil.rmtree': mock_shutil_rmtree_base,
        'app.tasks.process_audio_task.retry': mock_task_retry, # Mock the retry method
        'app.tasks.extract_audio_metadata': mock_extract_metadata, # Mock mutagen helper
        'app.tasks.get_audio_duration_ms': mock_get_duration_ffprobe # Mock ffprobe helper
    }

    exit_stack = ExitStack()
    for target, mock_obj in patches_dict.items():
        exit_stack.enter_context(patch(target, mock_obj))

    yield {
        "db_session": mock_db_session, "track": mock_track, "run": mock_subprocess_run,
        "get_uploader": mock_get_uploader, "uploader": mock_uploader_instance,
        "os_remove": mock_os_remove,
        "retry_mock": mock_task_retry,
        "cleanup_mock": mock_shutil_rmtree_base,
        "extract_metadata_mock": mock_extract_metadata,
        "get_duration_ffprobe_mock": mock_get_duration_ffprobe
    }

    exit_stack.close()


# --- Task Execution Tests ---

def test_process_audio_metadata_extracted_and_used(app, mock_task_deps):
    """Test that extracted metadata is used for missing fields."""
    mock_run = mock_task_deps['run']
    mock_track = mock_task_deps['track'] # User provided Title, others are None
    mock_extract_metadata = mock_task_deps['extract_metadata_mock']
    mock_get_duration = mock_task_deps['get_duration_ffprobe_mock']
    mock_uploader = mock_task_deps['uploader']
    mock_extract_metadata.return_value = {
        'title': "Extracted Title", 'artist': "Extracted Artist", 'album': "Extracted Album",
        'tracknumber': 5, 'duration_ms': 190000
    }
    ffmpeg_result = MagicMock(stdout='', stderr='', returncode=0)
    mock_run.return_value = ffmpeg_result # Only ffmpeg runs
    mock_uploader.upload.return_value = ("/processed/1/1/manifest.m3u8", "HLS")

    with app.app_context():
         process_audio_task.apply(args=[1, "/tmp/input.mp3"], kwargs={'output_format': "HLS"}).get()

    mock_extract_metadata.assert_called_once_with("/tmp/input.mp3")
    mock_get_duration.assert_not_called() # ffprobe duration not needed if mutagen found it
    assert mock_track.title == "User Title" # Preserved
    assert mock_track.artist == "Extracted Artist"; assert mock_track.album == "Extracted Album"
    assert mock_track.track_number == 5; assert mock_track.duration_ms == 190000
    assert mock_track.status == TrackStatus.READY
    assert mock_task_deps['db_session'].commit.call_count == 2

def test_process_audio_ffprobe_duration_used(app, mock_task_deps):
    """Test that ffprobe duration is used if mutagen fails and title is preserved.""" # Updated docstring
    mock_run = mock_task_deps['run']
    mock_track = mock_task_deps['track'] # Gets track with title="User Title" from fixture
    mock_extract_metadata = mock_task_deps['extract_metadata_mock']
    mock_get_duration = mock_task_deps['get_duration_ffprobe_mock']
    mock_uploader = mock_task_deps['uploader']

    # Simulate mutagen NOT finding duration, but finding title/artist
    mock_extract_metadata.return_value = {'title': 'Extracted Title', 'artist': 'Extracted Artist'}
    # Simulate ffprobe finding duration
    mock_get_duration.return_value = 210500

    ffmpeg_result = MagicMock(stdout='', stderr='', returncode=0)
    mock_run.return_value = ffmpeg_result
    mock_uploader.upload.return_value = ("/processed/1/1/manifest.m3u8", "HLS")

    with app.app_context():
         process_audio_task.apply(args=[1, "/tmp/input.mp3"], kwargs={'output_format': "HLS"}).get()

    mock_extract_metadata.assert_called_once_with("/tmp/input.mp3")
    mock_get_duration.assert_called_once_with("/tmp/input.mp3") # ffprobe WAS called

    assert mock_track.title == "User Title" # Existing title should be preserved
    assert mock_track.artist == "Extracted Artist" # Extracted artist used (was None initially)
    assert mock_track.duration_ms == 210500 # Used ffprobe duration

    assert mock_track.status == TrackStatus.READY

def test_process_audio_success_hls(app, mock_task_deps):
    mock_run = mock_task_deps['run']
    mock_track = mock_task_deps['track']
    mock_uploader = mock_task_deps['uploader']; mock_os_remove = mock_task_deps['os_remove']
    mock_extract_metadata = mock_task_deps['extract_metadata_mock']
    mock_get_duration = mock_task_deps['get_duration_ffprobe_mock']
    mock_extract_metadata.return_value = {} # No metadata found
    mock_get_duration.return_value = 185100 # Duration from ffprobe
    ffmpeg_result = MagicMock(stdout='', stderr='', returncode=0)
    mock_run.return_value = ffmpeg_result
    mock_uploader.upload.return_value = ("/processed/1/1/manifest.m3u8", "HLS")
    with app.app_context():
         result = process_audio_task.apply(args=[1, "/tmp/test.mp3"], kwargs={'output_format': "HLS"}).get()
    assert result is None; assert mock_track.status == TrackStatus.READY
    assert mock_track.duration_ms == 185100; assert mock_track.error_message is None
    assert mock_track.manifest_type == ManifestType.HLS; assert mock_track.manifest_url == "/processed/1/1/manifest.m3u8"
    assert mock_task_deps['db_session'].commit.call_count == 2; assert mock_run.call_count == 1
    ffmpeg_call_args = mock_run.call_args[0][0]; assert 'hls' in ffmpeg_call_args; assert 'manifest.m3u8' in ffmpeg_call_args[-1]
    mock_task_deps['get_uploader'].assert_called_once(); mock_uploader.upload.assert_called_once_with(source_dir=ANY, user_id=1, track_id=1)
    mock_uploader.cleanup_source.assert_called_once_with(ANY); mock_os_remove.assert_called_once_with("/tmp/test.mp3")

def test_process_audio_success_dash(app, mock_task_deps):
    mock_run = mock_task_deps['run']; mock_track = mock_task_deps['track']
    mock_uploader = mock_task_deps['uploader']; mock_os_remove = mock_task_deps['os_remove']
    mock_extract_metadata = mock_task_deps['extract_metadata_mock']
    mock_get_duration = mock_task_deps['get_duration_ffprobe_mock']
    mock_extract_metadata.return_value = {}
    mock_get_duration.return_value = 120000
    ffmpeg_result = MagicMock(stdout='', stderr='', returncode=0)
    mock_run.return_value = ffmpeg_result
    mock_uploader.upload.return_value = ("/processed/1/1/manifest.mpd", "DASH")
    with app.app_context():
         result = process_audio_task.apply(args=[1, "/tmp/test.mp3"], kwargs={'output_format': "DASH"}).get()
    assert result is None; assert mock_track.status == TrackStatus.READY
    assert mock_track.manifest_type == ManifestType.DASH; assert mock_track.manifest_url == "/processed/1/1/manifest.mpd"
    assert mock_track.duration_ms == 120000; assert mock_task_deps['db_session'].commit.call_count == 2
    ffmpeg_call_args = mock_run.call_args[0][0]; assert 'dash' in ffmpeg_call_args; assert 'manifest.mpd' in ffmpeg_call_args[-1]
    mock_uploader.upload.assert_called_once(); mock_uploader.cleanup_source.assert_called_once()
    mock_os_remove.assert_called_once_with("/tmp/test.mp3")

# --- CORRECTED RETRY TEST ---
def test_process_audio_ffmpeg_failure(app, mock_task_deps):
    """Test handling of FFmpeg execution failure and retry."""
    mock_run = mock_task_deps['run']
    mock_track = mock_task_deps['track']
    mock_retry = mock_task_deps['retry_mock'] # Get the mock for the retry method
    mock_os_remove = mock_task_deps['os_remove']
    mock_extract_metadata = mock_task_deps['extract_metadata_mock']
    mock_get_duration = mock_task_deps['get_duration_ffprobe_mock']
    mock_extract_metadata.return_value = {}
    mock_get_duration.return_value = 10000
    ffmpeg_error = subprocess.CalledProcessError(1, "cmd", stderr="FFmpeg failed badly")
    # Make ffmpeg call fail (subprocess.run mock)
    mock_run.side_effect = ffmpeg_error

    with app.app_context():
        # Run the task; apply().get() should return None because the mocked retry
        # doesn't actually raise Retry out of the eager execution context.
        result = process_audio_task.apply(
             args=[1, "/tmp/test.mp3"],
             kwargs={'output_format': "HLS"}
         ).get()

    # Assert state AFTER the mocked retry should have been called
    assert result is None # Task completes its execution flow, ends by calling mocked retry
    assert mock_track.status == TrackStatus.ERROR
    assert mock_track.error_message is not None
    assert "CalledProcessError" in mock_track.error_message
    assert "FFmpeg failed badly" in mock_track.error_message # Check stderr inclusion
    assert mock_task_deps['db_session'].commit.call_count == 2 # PROCESSING, then ERROR
    mock_retry.assert_called_once() # Assert the mocked retry method was called
    mock_os_remove.assert_not_called() # File kept on failure

# Use a specific patch for this test to make retry raise MaxRetriesExceededError
@patch('app.tasks.process_audio_task.retry', side_effect=MaxRetriesExceededError)
def test_process_audio_max_retries_exceeded(mock_retry_method_override, app, mock_task_deps):
    """Test behavior when max retries are exceeded after failure."""
    mock_run = mock_task_deps['run']
    mock_track = mock_task_deps['track']
    mock_extract_metadata = mock_task_deps['extract_metadata_mock']
    mock_get_duration = mock_task_deps['get_duration_ffprobe_mock']
    mock_extract_metadata.return_value = {}
    mock_get_duration.return_value = 10000
    # Make ffmpeg run fail
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="FFmpeg fails again")

    with app.app_context():
          # Task catches MaxRetriesExceededError internally, apply().get() returns None
          result = process_audio_task.apply(
              args=[1, "/tmp/test.mp3"],
              kwargs={'output_format': "HLS"}
          ).get()

    assert result is None
    assert mock_track.status == TrackStatus.ERROR
    assert mock_track.error_message is not None
    assert "CalledProcessError" in mock_track.error_message
    assert mock_task_deps['db_session'].commit.call_count == 2 # PROCESSING, ERROR
    # Assert the specifically patched retry was called (and raised MaxRetries...)
    mock_retry_method_override.assert_called_once()

# --- CORRECTED RETRY TEST ---
def test_process_audio_uploader_failure(app, mock_task_deps):
    """Test handling failure during the upload step."""
    mock_run = mock_task_deps['run']
    mock_track = mock_task_deps['track']
    mock_uploader = mock_task_deps['uploader']
    mock_retry = mock_task_deps['retry_mock'] # Get the mock for the retry method
    mock_extract_metadata = mock_task_deps['extract_metadata_mock']
    mock_get_duration = mock_task_deps['get_duration_ffprobe_mock']
    mock_extract_metadata.return_value = {}
    mock_get_duration.return_value = 10000
    # Simulate ffmpeg success
    ffmpeg_result = MagicMock(stdout='', stderr='', returncode=0)
    mock_run.return_value = ffmpeg_result
    # Simulate uploader failure
    mock_uploader.upload.side_effect = UploaderError("Upload failed!")

    with app.app_context():
        # Run the task; apply().get() should return None
        result = process_audio_task.apply(
             args=[1, "/tmp/test.mp3"],
             kwargs={'output_format': "HLS"}
         ).get()

    # Assert state AFTER the mocked retry should have been called
    assert result is None
    assert mock_track.status == TrackStatus.ERROR
    assert mock_track.error_message == "UploaderError: Upload failed!"
    assert mock_task_deps['db_session'].commit.call_count == 2
    mock_retry.assert_called_once() # Assert the mocked retry method was called


def test_process_audio_track_not_found(app, mock_task_deps):
    """Test task behavior when the track ID does not exist."""
    mock_db_session = mock_task_deps['db_session']
    mock_run = mock_task_deps['run']
    mock_os_remove = mock_task_deps['os_remove']
    mock_retry = mock_task_deps['retry_mock']
    mock_db_session.get.return_value = None # Simulate track not found

    with app.app_context():
        result = process_audio_task.apply(
            args=[999, "/tmp/orphan.mp3"], kwargs={'output_format': "HLS"}
        ).get()

    assert result is None
    mock_db_session.get.assert_called_once_with(Track, 999)
    mock_os_remove.assert_called_once_with("/tmp/orphan.mp3")
    mock_run.assert_not_called()
    mock_task_deps['get_uploader'].assert_not_called()
    mock_retry.assert_not_called()
    assert mock_db_session.commit.call_count == 0
