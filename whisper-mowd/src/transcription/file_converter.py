"""
File converter for audio and video files
Handles conversion between different formats using FFmpeg
"""

import os
import logging
import tempfile
import subprocess
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("file-converter")

class AudioFileConverter:
    """
    Handles conversion of various audio and video formats to formats
    compatible with Whisper (MP3, WAV)
    """
    
    # List of extensions that may need conversion
    VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']
    UNCOMMON_AUDIO = ['.m4a', '.aac', '.wma', '.ogg', '.flac']
    WHISPER_COMPATIBLE = ['.mp3', '.wav']
    
    def __init__(self, default_output_format="mp3", temp_dir=None):
        """
        Initialize the file converter
        
        Args:
            default_output_format: Default format to convert to (mp3 or wav)
            temp_dir: Directory for temporary files (None = system default)
        """
        self.default_output_format = default_output_format
        self.temp_dir = temp_dir
        
    def needs_conversion(self, file_path):
        """
        Check if a file needs conversion for Whisper compatibility
        
        Args:
            file_path: Path to check
            
        Returns:
            Boolean indicating if conversion is needed
        """
        suffix = Path(file_path).suffix.lower()
        return (suffix in self.VIDEO_EXTENSIONS or 
                suffix in self.UNCOMMON_AUDIO)
    
    def convert_to_audio(self, file_path, output_format=None):
        """
        Convert video or non-standard audio files to mp3/wav for Whisper processing
        Uses ffmpeg to handle the conversion
        
        Args:
            file_path: Path to the input file
            output_format: Format to convert to (mp3 or wav); uses default if None
            
        Returns:
            Path to the converted audio file (or original if no conversion needed)
        """
        file_path = Path(file_path)
        
        # Use default format if none specified
        if output_format is None:
            output_format = self.default_output_format
            
        # Validate output format
        if output_format not in ["mp3", "wav"]:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Check if conversion is needed
        if not self.needs_conversion(file_path):
            logger.info(f"No conversion needed for {file_path}")
            return str(file_path)
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(
            suffix=f".{output_format}", 
            delete=False,
            dir=self.temp_dir
        ) as tmp_file:
            output_path = tmp_file.name
        
        logger.info(f"Converting {file_path.suffix} file to {output_format} using ffmpeg")
        
        try:
            # Run ffmpeg to extract audio
            cmd = [
                "ffmpeg", 
                "-i", str(file_path), 
                "-vn",                   # No video
                "-ar", "44100",          # 44.1kHz sample rate
                "-ac", "2",              # Stereo
                "-ab", "192k",           # 192kbps bitrate
                "-f", output_format,     # Output format
                "-y",                    # Overwrite output
                output_path
            ]
            
            # Run the command and capture output
            process = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            if process.returncode != 0:
                logger.error(f"FFmpeg error: {process.stderr}")
                raise RuntimeError(f"Failed to convert file: {process.stderr}")
            
            logger.info(f"Conversion successful: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            # Clean up temp file if conversion failed
            if os.path.exists(output_path):
                os.unlink(output_path)
            raise
    
    def cleanup_temp_file(self, file_path):
        """
        Remove a temporary file created during conversion
        
        Args:
            file_path: Path to the temporary file
        """
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.info(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {file_path}: {e}")