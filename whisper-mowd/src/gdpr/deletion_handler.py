"""
GDPR Deletion Handler Lambda Function
Handles right to erasure requests under GDPR Article 17
"""

import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
cloudtrail = boto3.client('cloudtrail')

# Environment variables
AUDIO_BUCKET = os.environ['AUDIO_BUCKET']
TRANSCRIPT_BUCKET = os.environ['TRANSCRIPT_BUCKET']
SUMMARY_BUCKET = os.environ['SUMMARY_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE']
AUDIT_TABLE = os.environ['AUDIT_TABLE']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for GDPR deletion requests
    
    Args:
        event: API Gateway event containing deletion request
        context: Lambda context
        
    Returns:
        API response with deletion status
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('user_id')
        school_id = body.get('school_id')
        request_id = body.get('request_id')
        reason = body.get('reason', 'GDPR Article 17 Request')
        
        # Validate request
        if not user_id or not request_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields: user_id and request_id'
                })
            }
        
        # Log the deletion request
        audit_entry = create_audit_log(user_id, school_id, request_id, reason)
        
        # Find all data associated with the user
        user_data = find_user_data(user_id, school_id)
        
        # Delete data from all sources
        deletion_results = delete_user_data(user_data)
        
        # Update audit log with results
        update_audit_log(audit_entry['audit_id'], deletion_results)
        
        # Send confirmation
        send_deletion_confirmation(user_id, request_id, deletion_results)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'request_id': request_id,
                'status': 'completed',
                'deleted_items': deletion_results['summary'],
                'audit_id': audit_entry['audit_id']
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing deletion request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error processing deletion request'
            })
        }

def find_user_data(user_id: str, school_id: str = None) -> Dict[str, List[str]]:
    """
    Find all data associated with a user
    
    Args:
        user_id: User identifier
        school_id: Optional school identifier for filtering
        
    Returns:
        Dictionary of data locations
    """
    user_data = {
        'audio_files': [],
        'transcripts': [],
        'summaries': [],
        'metadata_items': []
    }
    
    try:
        # Query DynamoDB for user's lectures
        table = dynamodb.Table(METADATA_TABLE)
        
        # Use GSI if school_id provided
        if school_id:
            response = table.query(
                IndexName='SchoolIndex',
                KeyConditionExpression='school_id = :sid',
                FilterExpression='user_id = :uid',
                ExpressionAttributeValues={
                    ':sid': school_id,
                    ':uid': user_id
                }
            )
        else:
            # Scan for user_id (less efficient)
            response = table.scan(
                FilterExpression='user_id = :uid',
                ExpressionAttributeValues={
                    ':uid': user_id
                }
            )
        
        # Process items
        for item in response.get('Items', []):
            lecture_id = item['lecture_id']
            
            # Build S3 keys
            user_data['audio_files'].append(f"lectures/{lecture_id}.*")
            user_data['transcripts'].append(f"transcripts/{lecture_id}.txt")
            user_data['transcripts'].append(f"transcripts/{lecture_id}_with_timestamps.txt")
            user_data['summaries'].append(f"summaries/{lecture_id}.txt")
            user_data['metadata_items'].append(lecture_id)
        
        logger.info(f"Found {len(user_data['metadata_items'])} lectures for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error finding user data: {str(e)}")
        raise
    
    return user_data

def delete_user_data(user_data: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Delete all user data from various sources
    
    Args:
        user_data: Dictionary of data locations
        
    Returns:
        Deletion results summary
    """
    results = {
        'audio_deleted': 0,
        'transcripts_deleted': 0,
        'summaries_deleted': 0,
        'metadata_deleted': 0,
        'errors': [],
        'summary': {}
    }
    
    # Delete S3 objects
    for bucket, prefix, data_type in [
        (AUDIO_BUCKET, 'audio_files', 'audio'),
        (TRANSCRIPT_BUCKET, 'transcripts', 'transcripts'),
        (SUMMARY_BUCKET, 'summaries', 'summaries')
    ]:
        for key_pattern in user_data[prefix]:
            try:
                # List objects matching pattern
                if key_pattern.endswith('.*'):
                    # Handle wildcard for audio files
                    prefix_key = key_pattern[:-2]
                    response = s3.list_objects_v2(
                        Bucket=bucket,
                        Prefix=prefix_key
                    )
                    
                    for obj in response.get('Contents', []):
                        delete_s3_object(bucket, obj['Key'])
                        results[f'{data_type}_deleted'] += 1
                else:
                    # Direct key deletion
                    if check_s3_object_exists(bucket, key_pattern):
                        delete_s3_object(bucket, key_pattern)
                        results[f'{data_type}_deleted'] += 1
                        
            except Exception as e:
                error_msg = f"Error deleting {key_pattern} from {bucket}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
    
    # Delete DynamoDB items
    table = dynamodb.Table(METADATA_TABLE)
    for lecture_id in user_data['metadata_items']:
        try:
            table.delete_item(
                Key={'lecture_id': lecture_id}
            )
            results['metadata_deleted'] += 1
        except Exception as e:
            error_msg = f"Error deleting metadata for {lecture_id}: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
    
    # Create summary
    results['summary'] = {
        'total_audio_files': results['audio_deleted'],
        'total_transcripts': results['transcripts_deleted'],
        'total_summaries': results['summaries_deleted'],
        'total_metadata': results['metadata_deleted'],
        'total_errors': len(results['errors'])
    }
    
    return results

def delete_s3_object(bucket: str, key: str) -> None:
    """
    Delete a single S3 object with versioning support
    
    Args:
        bucket: S3 bucket name
        key: Object key
    """
    try:
        # Delete the object
        s3.delete_object(Bucket=bucket, Key=key)
        
        # Also delete all versions if versioning is enabled
        versions = s3.list_object_versions(
            Bucket=bucket,
            Prefix=key
        )
        
        for version in versions.get('Versions', []):
            s3.delete_object(
                Bucket=bucket,
                Key=key,
                VersionId=version['VersionId']
            )
            
        logger.info(f"Deleted {key} from {bucket}")
        
    except Exception as e:
        logger.error(f"Error deleting {key} from {bucket}: {str(e)}")
        raise

def check_s3_object_exists(bucket: str, key: str) -> bool:
    """
    Check if an S3 object exists
    
    Args:
        bucket: S3 bucket name
        key: Object key
        
    Returns:
        True if object exists
    """
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.NoSuchKey:
        return False
    except Exception as e:
        logger.error(f"Error checking object {key} in {bucket}: {str(e)}")
        return False

def create_audit_log(user_id: str, school_id: str, request_id: str, reason: str) -> Dict[str, str]:
    """
    Create an audit log entry for the deletion request
    
    Args:
        user_id: User identifier
        school_id: School identifier
        request_id: GDPR request ID
        reason: Deletion reason
        
    Returns:
        Audit entry details
    """
    audit_id = f"GDPR-{request_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    audit_entry = {
        'audit_id': audit_id,
        'request_id': request_id,
        'user_id': user_id,
        'school_id': school_id,
        'reason': reason,
        'request_time': datetime.utcnow().isoformat(),
        'status': 'in_progress',
        'ttl': int((datetime.utcnow().timestamp())) + (365 * 24 * 60 * 60)  # 1 year retention
    }
    
    try:
        table = dynamodb.Table(AUDIT_TABLE)
        table.put_item(Item=audit_entry)
        logger.info(f"Created audit log: {audit_id}")
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}")
        raise
    
    return audit_entry

def update_audit_log(audit_id: str, results: Dict[str, Any]) -> None:
    """
    Update audit log with deletion results
    
    Args:
        audit_id: Audit entry ID
        results: Deletion results
    """
    try:
        table = dynamodb.Table(AUDIT_TABLE)
        table.update_item(
            Key={'audit_id': audit_id},
            UpdateExpression='SET #status = :status, completion_time = :time, results = :results',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'completed' if not results['errors'] else 'completed_with_errors',
                ':time': datetime.utcnow().isoformat(),
                ':results': results['summary']
            }
        )
        logger.info(f"Updated audit log: {audit_id}")
    except Exception as e:
        logger.error(f"Error updating audit log: {str(e)}")

def send_deletion_confirmation(user_id: str, request_id: str, results: Dict[str, Any]) -> None:
    """
    Send confirmation of deletion (placeholder for notification service)
    
    Args:
        user_id: User identifier
        request_id: Request ID
        results: Deletion results
    """
    # In production, this would send an email or notification
    logger.info(f"Deletion completed for user {user_id}, request {request_id}")
    logger.info(f"Results: {json.dumps(results['summary'])}")
    
    # Log to CloudTrail for compliance
    try:
        cloudtrail.put_events(
            Records=[
                {
                    'EventTime': datetime.utcnow(),
                    'EventName': 'GDPRDeletionCompleted',
                    'EventSource': 'mowd.whisper',
                    'Resources': [
                        {
                            'ResourceType': 'User',
                            'ResourceName': user_id
                        }
                    ],
                    'CloudTrailEvent': json.dumps({
                        'requestId': request_id,
                        'results': results['summary']
                    })
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error logging to CloudTrail: {str(e)}")