"""
Transcription module for Whisper MOWD
Handles audio file processing and speech-to-text conversion
"""

from .whisper_service import WhisperTranscriber
from .file_converter import AudioFileConverter

__all__ = ['WhisperTranscriber', 'AudioFileConverter']