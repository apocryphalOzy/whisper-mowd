"""
Secure AWS Storage Implementation
Enhanced version with KMS encryption and security features
"""

import os
import json
import logging
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from ..logging.structured_logger import get_logger

# Initialize structured logger
logger = get_logger("secure-aws-storage")

class SecureAWSStorage:
    """
    Secure AWS storage with KMS encryption and audit logging
    """
    
    def __init__(self, audio_bucket=None, transcript_bucket=None, summary_bucket=None,
                 metadata_table=None, region=None):
        """
        Initialize secure AWS storage
        
        Args:
            audio_bucket: S3 bucket for audio files
            transcript_bucket: S3 bucket for transcripts
            summary_bucket: S3 bucket for summaries
            metadata_table: DynamoDB table for metadata
            region: AWS region
        """
        # Get settings from params or environment
        self.audio_bucket = audio_bucket or os.getenv("S3_LECTURE_BUCKET")
        self.transcript_bucket = transcript_bucket or os.getenv("S3_TRANSCRIPT_BUCKET")
        self.summary_bucket = summary_bucket or os.getenv("S3_SUMMARY_BUCKET")
        self.metadata_table_name = metadata_table or os.getenv("DYNAMODB_TABLE")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        # KMS key aliases
        self.kms_audio_alias = os.getenv("KMS_AUDIO_ALIAS", "alias/mowd-audio-prod")
        self.kms_transcript_alias = os.getenv("KMS_TRANSCRIPT_ALIAS", "alias/mowd-transcript-prod")
        self.kms_summary_alias = os.getenv("KMS_SUMMARY_ALIAS", "alias/mowd-summary-prod")
        
        # Validate required settings
        if not all([self.audio_bucket, self.transcript_bucket, self.summary_bucket, 
                   self.metadata_table_name]):
            raise ValueError("Missing required AWS configuration")
        
        # Configure boto3 with security best practices
        config = Config(
            region_name=self.region,
            signature_version='v4',
            retries={
                'max_attempts': 10,
                'mode': 'adaptive'
            }
        )
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', config=config)
        self.dynamodb = boto3.resource('dynamodb', config=config)
        self.metadata_table = self.dynamodb.Table(self.metadata_table_name)
        self.kms_client = boto3.client('kms', config=config)
        
        logger.info("Secure AWS storage initialized", 
                   audio_bucket=self.audio_bucket,
                   transcript_bucket=self.transcript_bucket,
                   environment=os.getenv('ENVIRONMENT', 'dev'))
    
    def save_audio(self, file_path: str, lecture_id: Optional[str] = None, 
                  user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Save an audio file to S3 with KMS encryption
        
        Args:
            file_path: Path to the audio file
            lecture_id: Optional ID for the lecture
            user_context: User context for audit logging
            
        Returns:
            lecture_id
        """
        file_path = Path(file_path)
        
        # Generate lecture_id if not provided
        if lecture_id is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            lecture_id = f"{timestamp}_{file_path.stem}"
        
        # Calculate file hash for integrity
        file_hash = self._calculate_file_hash(file_path)
        
        # Define S3 key
        s3_key = f"lectures/{lecture_id}{file_path.suffix}"
        
        try:
            # Get KMS key ID
            kms_key_id = self._get_kms_key_id(self.kms_audio_alias)
            
            # Upload to S3 with KMS encryption
            with open(file_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.audio_bucket,
                    Key=s3_key,
                    Body=f,
                    ServerSideEncryption='aws:kms',
                    SSEKMSKeyId=kms_key_id,
                    ContentType=self._get_content_type(file_path.suffix),
                    Metadata={
                        'lecture_id': lecture_id,
                        'upload_time': datetime.utcnow().isoformat(),
                        'file_hash': file_hash,
                        'original_filename': file_path.name
                    },
                    StorageClass='STANDARD_IA'  # Cost optimization
                )
            
            # Log successful upload
            logger.info("Audio file uploaded successfully",
                       lecture_id=lecture_id,
                       s3_key=s3_key,
                       file_size=file_path.stat().st_size,
                       file_hash=file_hash)
            
            # Audit trail
            if user_context:
                logger.audit_trail(
                    action="UPLOAD_AUDIO",
                    resource=s3_key,
                    user_id=user_context.get('user_id'),
                    result="success",
                    details={'file_size': file_path.stat().st_size}
                )
            
            return lecture_id
            
        except ClientError as e:
            logger.error("Failed to upload audio file",
                        error=str(e),
                        lecture_id=lecture_id,
                        error_code=e.response['Error']['Code'])
            raise
    
    def get_audio_url(self, lecture_id: str, expiry_seconds: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for audio file access
        
        Args:
            lecture_id: ID of the lecture
            expiry_seconds: URL expiry time in seconds
            
        Returns:
            Presigned URL or None if file not found
        """
        # Try common audio extensions
        for ext in ['.mp3', '.wav', '.m4a', '.mp4']:
            s3_key = f"lectures/{lecture_id}{ext}"
            
            try:
                # Check if file exists
                self.s3_client.head_object(Bucket=self.audio_bucket, Key=s3_key)
                
                # Generate presigned URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.audio_bucket,
                        'Key': s3_key
                    },
                    ExpiresIn=expiry_seconds
                )
                
                logger.info("Generated presigned URL",
                           lecture_id=lecture_id,
                           expiry_seconds=expiry_seconds)
                
                return url
                
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    continue
                else:
                    logger.error("Error generating presigned URL",
                                error=str(e),
                                lecture_id=lecture_id)
                    return None
        
        logger.warning("Audio file not found", lecture_id=lecture_id)
        return None
    
    def save_transcript(self, lecture_id: str, transcript_text: str,
                       user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Save a transcript to S3 with KMS encryption
        
        Args:
            lecture_id: ID of the lecture
            transcript_text: Transcript text
            user_context: User context for audit logging
            
        Returns:
            S3 URI of the saved transcript
        """
        s3_key = f"transcripts/{lecture_id}.txt"
        
        try:
            # Get KMS key ID
            kms_key_id = self._get_kms_key_id(self.kms_transcript_alias)
            
            # Calculate content hash
            content_hash = hashlib.sha256(transcript_text.encode()).hexdigest()
            
            self.s3_client.put_object(
                Bucket=self.transcript_bucket,
                Key=s3_key,
                Body=transcript_text.encode('utf-8'),
                ServerSideEncryption='aws:kms',
                SSEKMSKeyId=kms_key_id,
                ContentType='text/plain; charset=utf-8',
                Metadata={
                    'lecture_id': lecture_id,
                    'content_hash': content_hash,
                    'word_count': str(len(transcript_text.split()))
                }
            )
            
            s3_uri = f"s3://{self.transcript_bucket}/{s3_key}"
            
            logger.info("Transcript saved successfully",
                       lecture_id=lecture_id,
                       s3_uri=s3_uri,
                       word_count=len(transcript_text.split()))
            
            # Audit trail
            if user_context:
                logger.audit_trail(
                    action="SAVE_TRANSCRIPT",
                    resource=s3_key,
                    user_id=user_context.get('user_id'),
                    result="success"
                )
            
            return s3_uri
            
        except ClientError as e:
            logger.error("Failed to save transcript",
                        error=str(e),
                        lecture_id=lecture_id)
            raise
    
    def save_metadata(self, lecture_id: str, metadata: Dict[str, Any],
                     user_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save metadata to DynamoDB with TTL
        
        Args:
            lecture_id: ID of the lecture
            metadata: Metadata dictionary
            user_context: User context for audit logging
            
        Returns:
            True if successful
        """
        # Add timestamps if not present
        current_time = datetime.utcnow()
        if 'created_at' not in metadata:
            metadata['created_at'] = current_time.isoformat()
        if 'updated_at' not in metadata:
            metadata['updated_at'] = current_time.isoformat()
        
        # Add TTL for automatic cleanup (18 months)
        ttl_date = current_time + timedelta(days=548)
        metadata['ttl'] = int(ttl_date.timestamp())
        
        # Add lecture_id and user context
        metadata['lecture_id'] = lecture_id
        if user_context:
            metadata['user_id'] = user_context.get('user_id')
            metadata['school_id'] = user_context.get('school_id')
        
        try:
            # Use conditional put to prevent overwrites
            self.metadata_table.put_item(
                Item=metadata,
                ConditionExpression='attribute_not_exists(lecture_id)'
            )
            
            logger.info("Metadata saved successfully",
                       lecture_id=lecture_id,
                       has_user_context=bool(user_context))
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning("Metadata already exists",
                             lecture_id=lecture_id)
                # Update instead
                return self._update_metadata(lecture_id, metadata)
            else:
                logger.error("Failed to save metadata",
                           error=str(e),
                           lecture_id=lecture_id)
                raise
    
    def _update_metadata(self, lecture_id: str, metadata: Dict[str, Any]) -> bool:
        """Update existing metadata"""
        try:
            # Build update expression
            update_expr = "SET updated_at = :updated_at"
            expr_values = {":updated_at": datetime.utcnow().isoformat()}
            
            # Add other fields to update
            for key, value in metadata.items():
                if key not in ['lecture_id', 'created_at']:
                    update_expr += f", {key} = :{key}"
                    expr_values[f":{key}"] = value
            
            self.metadata_table.update_item(
                Key={'lecture_id': lecture_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to update metadata",
                        error=str(e),
                        lecture_id=lecture_id)
            return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_kms_key_id(self, alias: str) -> str:
        """Get KMS key ID from alias"""
        try:
            response = self.kms_client.describe_key(KeyId=alias)
            return response['KeyMetadata']['KeyId']
        except Exception as e:
            logger.error("Failed to get KMS key",
                        alias=alias,
                        error=str(e))
            raise
    
    def _get_content_type(self, extension: str) -> str:
        """Get content type for file extension"""
        content_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4',
            '.txt': 'text/plain',
            '.json': 'application/json'
        }
        return content_types.get(extension.lower(), 'application/octet-stream')