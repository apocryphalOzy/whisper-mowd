"""
Local file storage implementation
Handles saving and retrieving files and metadata locally
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("local-storage")

class LocalStorage:
    """
    Handles local file storage for development and testing
    """
    
    def __init__(self, base_dir="./data"):
        """
        Initialize local storage with base directory
        
        Args:
            base_dir: Base directory for storage
        """
        self.base_dir = Path(base_dir)
        
        # Create subdirectories
        self.audio_dir = self.base_dir / "audio"
        self.transcript_dir = self.base_dir / "transcripts"
        self.summary_dir = self.base_dir / "summaries"
        self.metadata_dir = self.base_dir / "metadata"
        
        # Create directories if they don't exist
        self._create_directories()
        
        logger.info(f"Local storage initialized at {self.base_dir}")
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        for directory in [self.audio_dir, self.transcript_dir, 
                          self.summary_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def save_audio(self, file_path, lecture_id=None):
        """
        Save an audio file to storage
        
        Args:
            file_path: Path to the audio file
            lecture_id: Optional ID for the lecture (generated if None)
            
        Returns:
            lecture_id
        """
        file_path = Path(file_path)
        
        # Generate lecture_id if not provided
        if lecture_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            lecture_id = f"{timestamp}_{file_path.stem}"
        
        # Get the destination path
        dest_path = self.audio_dir / f"{lecture_id}{file_path.suffix}"
        
        # Copy the file
        try:
            shutil.copy2(file_path, dest_path)
            logger.info(f"Saved audio file to {dest_path}")
            return lecture_id
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            raise
    
    def get_audio_path(self, lecture_id):
        """
        Get the path to an audio file
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Path to the audio file or None if not found
        """
        # Check for files with any extension
        for file_path in self.audio_dir.glob(f"{lecture_id}.*"):
            return file_path
        
        logger.warning(f"Audio file not found for lecture_id: {lecture_id}")
        return None
    
    def save_transcript(self, lecture_id, transcript_text):
        """
        Save a transcript to storage
        
        Args:
            lecture_id: ID of the lecture
            transcript_text: Transcript text
            
        Returns:
            Path to the saved transcript
        """
        if not transcript_text:
            logger.warning(f"Attempting to save empty transcript for lecture_id: {lecture_id}")
    
        transcript_path = self.transcript_dir / f"{lecture_id}.txt"
        
        try:
            with open(transcript_path, 'w', encoding='utf-8') as f:
                bytes_written = f.write(transcript_text)
                f.flush()  # Ensure data is written to disk
                os.fsync(f.fileno())  # Force OS to flush file buffers
            
            logger.info(f"Saved transcript to {transcript_path} ({bytes_written} bytes written)")
            
            # Verify file was written correctly
            if os.path.exists(transcript_path) and os.path.getsize(transcript_path) > 0:
                logger.info(f"Verified file has {os.path.getsize(transcript_path)} bytes")
            else:
                logger.error(f"File verification failed - file may be empty: {transcript_path}")
                
            return transcript_path
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
            raise
    def save_summary(self, lecture_id, summary_text):
        """
        Save a summary to storage
        
        Args:
            lecture_id: ID of the lecture
            summary_text: Summary text
            
        Returns:
            Path to the saved summary
        """
        # Don't save if summary is None
        if summary_text is None:
            logger.info(f"No summary to save for lecture_id: {lecture_id}")
            return None
            
        summary_path = self.summary_dir / f"{lecture_id}.txt"
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_text)
            
            logger.info(f"Saved summary to {summary_path}")
            return summary_path
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            raise
    
    def save_metadata(self, lecture_id, metadata):
        """
        Save metadata for a lecture
        
        Args:
            lecture_id: ID of the lecture
            metadata: Dictionary of metadata
            
        Returns:
            Path to the saved metadata
        """
        metadata_path = self.metadata_dir / f"{lecture_id}.json"
        
        # Add timestamp if not present
        if 'created_at' not in metadata:
            metadata['created_at'] = datetime.now().isoformat()
        if 'updated_at' not in metadata:
            metadata['updated_at'] = datetime.now().isoformat()
        
        # Add lecture_id to metadata
        metadata['lecture_id'] = lecture_id
        
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved metadata to {metadata_path}")
            return metadata_path
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise
    
    def get_transcript(self, lecture_id):
        """
        Get a transcript from storage
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Transcript text or None if not found
        """
        transcript_path = self.transcript_dir / f"{lecture_id}.txt"
        
        if not transcript_path.exists():
            logger.warning(f"Transcript not found for lecture_id: {lecture_id}")
            return None
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read transcript: {e}")
            return None
    
    def get_summary(self, lecture_id):
        """
        Get a summary from storage
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Summary text or None if not found
        """
        summary_path = self.summary_dir / f"{lecture_id}.txt"
        
        if not summary_path.exists():
            logger.warning(f"Summary not found for lecture_id: {lecture_id}")
            return None
        
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read summary: {e}")
            return None
    
    def get_metadata(self, lecture_id):
        """
        Get metadata for a lecture
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Metadata dictionary or None if not found
        """
        metadata_path = self.metadata_dir / f"{lecture_id}.json"
        
        if not metadata_path.exists():
            logger.warning(f"Metadata not found for lecture_id: {lecture_id}")
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metadata: {e}")
            return None
    
    def list_lectures(self, limit=100, offset=0):
        """
        List available lectures with pagination
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of lecture IDs
        """
        # Get all metadata files
        metadata_files = list(self.metadata_dir.glob("*.json"))
        
        # Sort by modification time (newest first)
        metadata_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Apply pagination
        metadata_files = metadata_files[offset:offset+limit]
        
        # Extract lecture IDs from filenames
        lecture_ids = [file.stem for file in metadata_files]
        
        return lecture_ids
    def save_transcript_with_timestamps(self, lecture_id, transcription_result):
        """
        Save a transcript with timestamps to storage
        
        Args:
            lecture_id: ID of the lecture
            transcription_result: Full transcription result with segments
            
        Returns:
            Path to the saved transcript
        """
        from src.transcription.utils import format_timestamp
        
        transcript_path = self.transcript_dir / f"{lecture_id}_with_timestamps.txt"
        
        try:
            with open(transcript_path, 'w', encoding='utf-8') as f:
                segments = transcription_result.get("segments", [])
                for segment in segments:
                    start_time = format_timestamp(segment["start"])
                    end_time = format_timestamp(segment["end"])
                    f.write(f"[{start_time} --> {end_time}] {segment['text']}\n")
            
            logger.info(f"Saved timestamped transcript to {transcript_path}")
            return transcript_path
        except Exception as e:
            logger.error(f"Failed to save timestamped transcript: {e}")
            raise