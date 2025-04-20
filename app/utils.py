import mutagen
import logging
import math
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.flac import FLAC, FLACNoHeaderError
from mutagen.mp4 import MP4, MP4StreamInfoError
from mutagen.oggvorbis import OggVorbis, OggVorbisHeaderError
# Add more imports as needed (e.g., mutagen.wave, mutagen.aiff)

log = logging.getLogger(__name__)

def extract_audio_metadata(filepath: str) -> dict:
    """
    Extracts common metadata tags from an audio file using mutagen.

    Args:
        filepath: The absolute path to the audio file.

    Returns:
        A dictionary containing extracted metadata (e.g., 'title', 'artist',
        'album', 'tracknumber', 'duration_ms'). Returns an empty dict on error
        or if no tags are found.
    """
    metadata = {}
    try:
        # Load the file based on likely types - add more as needed
        try:
            audio = mutagen.File(filepath, easy=True) # easy=True provides simpler tag access
            if audio is None:
                 # Try without easy=True if initial load fails or returns None
                 log.warning(f"Mutagen easy=True failed for {filepath}, trying specific types.")
                 audio = mutagen.File(filepath, easy=False)
                 if audio is None:
                      raise mutagen.MutagenError("Mutagen could not determine file type or load file.")
        except HeaderNotFoundError: # Specific MP3 header error
            log.warning(f"Could not find MP3 header for {filepath}. Trying without easy=True.")
            audio = MP3(filepath) # Try loading specifically as MP3
        except (FLACNoHeaderError, MP4StreamInfoError, OggVorbisHeaderError, mutagen.MutagenError) as e:
            log.warning(f"Error loading audio file {filepath} with mutagen: {e}. Cannot extract tags.")
            return metadata # Return empty if file loading fails

        if not audio:
             log.warning(f"Mutagen returned None for file: {filepath}")
             return metadata

        # Extract common tags (using 'easy' tags if available)
        # easy=True provides tags like 'title', 'artist' directly
        # easy=False provides format-specific tags like 'TIT2', 'TPE1' (ID3)
        if audio.tags:
            if hasattr(audio, 'easy') and audio.easy:
                tags_to_check = {'title': 'title', 'artist': 'artist', 'album': 'album', 'tracknumber': 'tracknumber'}
            else:
                # Map common ID3 tags (add more mappings for other formats if needed)
                tags_to_check = {'title': 'TIT2', 'artist': 'TPE1', 'album': 'TALB', 'tracknumber': 'TRCK'}
                # Handle other formats like MP4 (©nam, ©ART, ©alb, trkn) or Vorbis (TITLE, ARTIST, ALBUM, TRACKNUMBER)

            for meta_key, tag_key in tags_to_check.items():
                tag_value = audio.tags.get(tag_key)
                if tag_value:
                    # Mutagen often returns lists, take the first item
                    value = tag_value[0] if isinstance(tag_value, list) else tag_value
                    if isinstance(value, str) and value.strip():
                        # Special handling for track number
                        if meta_key == 'tracknumber':
                             try:
                                 # Handle "1/12" format
                                 metadata[meta_key] = int(value.split('/')[0])
                             except (ValueError, IndexError):
                                 metadata[meta_key] = None
                        else:
                             metadata[meta_key] = value.strip()
                    elif isinstance(value, int): # For track number if already int
                         if meta_key == 'tracknumber':
                              metadata[meta_key] = value
                    # Add more type checks if needed

        # Extract duration from info (more reliable)
        if audio.info and hasattr(audio.info, 'length') and audio.info.length > 0:
            duration_s = audio.info.length
            metadata['duration_ms'] = math.ceil(duration_s * 1000)

        # Clean up None values (already filtered by check during extraction)
        cleaned_metadata = {k: v for k, v in metadata.items() if v is not None}
        log.info(f"Extracted metadata for {filepath}: {cleaned_metadata}")
        return cleaned_metadata

    except Exception as e:
        log.error(f"Unexpected error extracting metadata from {filepath}: {e}", exc_info=True)
        return {} # Return empty dict on any unexpected error
