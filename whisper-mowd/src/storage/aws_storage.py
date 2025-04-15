"""
AWS storage implementation
Handles file and metadata storage in S3 and DynamoDB
"""

import os
import json
import logging
import tempfile
import boto3
from pathlib import Path
from datetime import datetime
from botocore.exceptions import ClientError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("aws-storage")

class AWSStorage:
    """
    Handles AWS storage for production deployment
    Uses S3 for file storage and DynamoDB for metadata
    """
    
    def __init__(self, audio_bucket=None, transcript_bucket=None, metadata_table=None, region=None):
        """
        Initialize AWS storage
        
        Args:
            audio_bucket: S3 bucket for audio files
            transcript_bucket: S3 bucket for transcripts and summaries
            metadata_table: DynamoDB table for metadata
            region: AWS region
        """
        # Get settings from params or environment
        self.audio_bucket = audio_bucket or os.getenv("S3_LECTURE_BUCKET")
        self.transcript_bucket = transcript_bucket or os.getenv("S3_TRANSCRIPT_BUCKET")
        self.metadata_table_name = metadata_table or os.getenv("DYNAMODB_TABLE")
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        
        # Validate required settings
        if not all([self.audio_bucket, self.transcript_bucket, self.metadata_table_name]):
            raise ValueError("Missing required AWS configuration. Set S3_LECTURE_BUCKET, S3_TRANSCRIPT_BUCKET, and DYNAMODB_TABLE.")
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.metadata_table = self.dynamodb.Table(self.metadata_table_name)
        
        logger.info(f"AWS storage initialized: audio={self.audio_bucket}, transcripts={self.transcript_bucket}, table={self.metadata_table_name}")
    
    def save_audio(self, file_path, lecture_id=None):
        """
        Save an audio file to S3
        
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
        
        # Define S3 key
        s3_key = f"lectures/{lecture_id}{file_path.suffix}"
        
        # Upload to S3
        try:
            self.s3_client.upload_file(
                str(file_path),
                self.audio_bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': self._get_content_type(file_path.suffix)
                }
            )
            
            logger.info(f"Uploaded audio file to s3://{self.audio_bucket}/{s3_key}")
            return lecture_id
            
        except ClientError as e:
            logger.error(f"Failed to upload audio file to S3: {e}")
            raise
    
    def get_audio_path(self, lecture_id):
        """
        Download an audio file from S3 to a temporary location
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Path to the temporary file containing the audio, or None if not found
        """
        # Try common audio extensions
        for ext in ['.mp3', '.wav', '.m4a', '.mp4']:
            s3_key = f"lectures/{lecture_id}{ext}"
            
            try:
                # Check if file exists
                self.s3_client.head_object(Bucket=self.audio_bucket, Key=s3_key)
                
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                temp_path = temp_file.name
                temp_file.close()
                
                # Download file
                self.s3_client.download_file(
                    self.audio_bucket,
                    s3_key,
                    temp_path
                )
                
                logger.info(f"Downloaded audio file from S3 to {temp_path}")
                return temp_path
                
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # File not found, try next extension
                    continue
                else:
                    logger.error(f"Error accessing S3: {e}")
                    return None
        
        logger.warning(f"Audio file not found for lecture_id: {lecture_id}")
        return None
    
    def save_transcript(self, lecture_id, transcript_text):
        """
        Save a transcript to S3
        
        Args:
            lecture_id: ID of the lecture
            transcript_text: Transcript text
            
        Returns:
            S3 URI of the saved transcript
        """
        s3_key = f"transcripts/{lecture_id}.txt"
        
        try:
            self.s3_client.put_object(
                Bucket=self.transcript_bucket,
                Key=s3_key,
                Body=transcript_text,
                ContentType='text/plain'
            )
            
            s3_uri = f"s3://{self.transcript_bucket}/{s3_key}"
            logger.info(f"Saved transcript to {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            logger.error(f"Failed to save transcript to S3: {e}")
            raise
    
    def save_summary(self, lecture_id, summary_text):
        """
        Save a summary to S3
        
        Args:
            lecture_id: ID of the lecture
            summary_text: Summary text
            
        Returns:
            S3 URI of the saved summary or None if summary is None
        """
        # Don't save if summary is None
        if summary_text is None:
            logger.info(f"No summary to save for lecture_id: {lecture_id}")
            return None
            
        s3_key = f"summaries/{lecture_id}.txt"
        
        try:
            self.s3_client.put_object(
                Bucket=self.transcript_bucket,
                Key=s3_key,
                Body=summary_text,
                ContentType='text/plain'
            )
            
            s3_uri = f"s3://{self.transcript_bucket}/{s3_key}"
            logger.info(f"Saved summary to {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            logger.error(f"Failed to save summary to S3: {e}")
            raise
    
    def save_metadata(self, lecture_id, metadata):
        """
        Save metadata for a lecture to DynamoDB
        
        Args:
            lecture_id: ID of the lecture
            metadata: Dictionary of metadata
            
        Returns:
            True if successful
        """
        # Add timestamps if not present
        current_time = datetime.now().isoformat()
        if 'created_at' not in metadata:
            metadata['created_at'] = current_time
        if 'updated_at' not in metadata:
            metadata['updated_at'] = current_time
        
        # Add lecture_id to metadata
        metadata['lecture_id'] = lecture_id
        
        try:
            self.metadata_table.put_item(Item=metadata)
            logger.info(f"Saved metadata to DynamoDB for lecture_id: {lecture_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to save metadata to DynamoDB: {e}")
            raise
    
    def get_transcript(self, lecture_id):
        """
        Get a transcript from S3
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Transcript text or None if not found
        """
        s3_key = f"transcripts/{lecture_id}.txt"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.transcript_bucket,
                Key=s3_key
            )
            
            transcript = response['Body'].read().decode('utf-8')
            logger.info(f"Retrieved transcript for lecture_id: {lecture_id}")
            return transcript
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Transcript not found for lecture_id: {lecture_id}")
                return None
            else:
                logger.error(f"Error retrieving transcript from S3: {e}")
                return None
    
    def get_summary(self, lecture_id):
        """
        Get a summary from S3
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Summary text or None if not found
        """
        s3_key = f"summaries/{lecture_id}.txt"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.transcript_bucket,
                Key=s3_key
            )
            
            summary = response['Body'].read().decode('utf-8')
            logger.info(f"Retrieved summary for lecture_id: {lecture_id}")
            return summary
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Summary not found for lecture_id: {lecture_id}")
                return None
            else:
                logger.error(f"Error retrieving summary from S3: {e}")
                return None
    
    def get_metadata(self, lecture_id):
        """
        Get metadata for a lecture from DynamoDB
        
        Args:
            lecture_id: ID of the lecture
            
        Returns:
            Metadata dictionary or None if not found
        """
        try:
            response = self.metadata_table.get_item(
                Key={'lecture_id': lecture_id}
            )
            
            metadata = response.get('Item')
            if metadata:
                logger.info(f"Retrieved metadata for lecture_id: {lecture_id}")
                return metadata
            else:
                logger.warning(f"Metadata not found for lecture_id: {lecture_id}")
                return None
                
        except ClientError as e:
            logger.error(f"Error retrieving metadata from DynamoDB: {e}")
            return None
    
    def list_lectures(self, limit=100, filter_expr=None):
        """
        List available lectures from DynamoDB
        
        Args:
            limit: Maximum number of items to return
            filter_expr: Optional filter expression for DynamoDB scan
            
        Returns:
            List of lecture metadata dictionaries
        """
        scan_params = {
            'Limit': limit
        }
        
        if filter_expr:
            scan_params['FilterExpression'] = filter_expr
        
        try:
            response = self.metadata_table.scan(**scan_params)
            
            lectures = response.get('Items', [])
            logger.info(f"Retrieved {len(lectures)} lectures from DynamoDB")
            return lectures
            
        except ClientError as e:
            logger.error(f"Error listing lectures from DynamoDB: {e}")
            return []
    
    def _get_content_type(self, extension):
        """
        Get the appropriate content type for a file extension
        
        Args:
            extension: File extension including the dot
            
        Returns:
            MIME content type string
        """
        content_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.txt': 'text/plain',
            '.json': 'application/json'
        }
        
        return content_types.get(extension.lower(), 'application/octet-stream')
    
    def save_transcript_with_timestamps(self, lecture_id, transcription_result):
        """
        Save a transcript with timestamps to S3
        
        Args:
            lecture_id: ID of the lecture
            transcription_result: Full transcription result with segments
            
        Returns:
            S3 URI of the saved transcript
        """
        from src.transcription.utils import format_timestamp
        
        s3_key = f"transcripts/{lecture_id}_with_timestamps.txt"
        
        try:
            # Build the timestamped transcript
            timestamped_text = ""
            segments = transcription_result.get("segments", [])
            for segment in segments:
                start_time = format_timestamp(segment["start"])
                end_time = format_timestamp(segment["end"])
                timestamped_text += f"[{start_time} --> {end_time}] {segment['text']}\n"
            
            # Save to S3
            self.s3_client.put_object(
                Bucket=self.transcript_bucket,
                Key=s3_key,
                Body=timestamped_text,
                ContentType='text/plain'
            )
            
            s3_uri = f"s3://{self.transcript_bucket}/{s3_key}"
            logger.info(f"Saved timestamped transcript to {s3_uri}")
            return s3_uri
            
        except Exception as e:
            logger.error(f"Failed to save timestamped transcript to S3: {e}")
            raise