"""
Utility functions for transcription module
Miscellaneous helper functions for audio processing and transcription
"""

import os
import logging
import tempfile
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("transcription-utils")

def get_audio_duration(file_path):
    """
    Get the duration of an audio file in seconds
    Uses ffprobe (ffmpeg) to get media information
    
    Args:
        file_path: Path to the audio or video file
        
    Returns:
        Duration in seconds (float) or None if error
    """
    try:
        import subprocess
        
        # Use ffprobe to get duration
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            str(file_path)
        ]
        
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return duration
        else:
            logger.error(f"FFprobe error: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting audio duration: {e}")
        return None

def create_temp_dir(prefix="whisper_mowd_"):
    """
    Create a temporary directory for processing files
    
    Args:
        prefix: Prefix for the temporary directory name
        
    Returns:
        Path to the temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    logger.info(f"Created temporary directory: {temp_dir}")
    return temp_dir

def cleanup_temp_dir(dir_path):
    """
    Remove a temporary directory and its contents
    
    Args:
        dir_path: Path to the directory to remove
    """
    try:
        import shutil
        shutil.rmtree(dir_path)
        logger.info(f"Removed temporary directory: {dir_path}")
    except Exception as e:
        logger.warning(f"Failed to remove temporary directory {dir_path}: {e}")

def format_timestamp(seconds):
    """
    Format seconds as HH:MM:SS
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_segments_as_srt(segments):
    """
    Format transcription segments as SRT format
    
    Args:
        segments: List of segments from Whisper transcription
        
    Returns:
        String in SRT subtitle format
    """
    srt_content = ""
    
    for i, segment in enumerate(segments):
        # Calculate start and end times in SRT format (HH:MM:SS,mmm)
        start_time = format_srt_timestamp(segment["start"])
        end_time = format_srt_timestamp(segment["end"])
        
        # Add segment number, timestamps, and text
        srt_content += f"{i+1}\n"
        srt_content += f"{start_time} --> {end_time}\n"
        srt_content += f"{segment['text'].strip()}\n\n"
    
    return srt_content

def format_srt_timestamp(seconds):
    """
    Format seconds as HH:MM:SS,mmm for SRT files
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"