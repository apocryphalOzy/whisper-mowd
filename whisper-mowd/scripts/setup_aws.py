#!/usr/bin/env python
"""
AWS setup script for Whisper MOWD
Creates required AWS resources for deployment
"""

import os
import sys
import argparse
import logging
import boto3
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("aws-setup")

# Load environment variables
load_dotenv()

def setup_s3_buckets(region, env, create_state_bucket=False):
    """
    Create S3 buckets for audio, transcripts, and optionally Terraform state
    
    Args:
        region: AWS region
        env: Environment name (dev, staging, prod)
        create_state_bucket: Whether to create a Terraform state bucket
        
    Returns:
        Dictionary with bucket names
    """
    s3 = boto3.client('s3', region_name=region)
    
    # Bucket names
    audio_bucket = f"mowd-whisper-lectures-{env}"
    transcript_bucket = f"mowd-whisper-transcripts-{env}"
    state_bucket = f"mowd-whisper-terraform-state-{env}" if create_state_bucket else None
    
    buckets_to_create = [
        (audio_bucket, "audio files"),
        (transcript_bucket, "transcripts and summaries")
    ]
    
    if create_state_bucket:
        buckets_to_create.append((state_bucket, "Terraform state"))
    
    # Create buckets
    for bucket_name, purpose in buckets_to_create:
        try:
            logger.info(f"Creating S3 bucket {bucket_name} for {purpose}...")
            
            # CreateBucketConfiguration is required for regions other than us-east-1
            if region == 'us-east-1':
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            
            # Enable versioning
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Enable encryption
            s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )
            
            # Add tags
            s3.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={
                    'TagSet': [
                        {
                            'Key': 'Project',
                            'Value': 'MOWD-Whisper'
                        },
                        {
                            'Key': 'Environment',
                            'Value': env
                        }
                    ]
                }
            )
            
            # Block public access for audio and transcript buckets
            if bucket_name != state_bucket:
                s3.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': True,
                        'IgnorePublicAcls': True,
                        'BlockPublicPolicy': True,
                        'RestrictPublicBuckets': True
                    }
                )
            
            logger.info(f"Successfully created bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Error creating bucket {bucket_name}: {e}")
            raise
    
    return {
        'audio_bucket': audio_bucket,
        'transcript_bucket': transcript_bucket,
        'state_bucket': state_bucket
    }

def setup_dynamodb_table(region, env):
    """
    Create DynamoDB table for lecture metadata
    
    Args:
        region: AWS region
        env: Environment name (dev, staging, prod)
        
    Returns:
        Table name
    """
    dynamodb = boto3.client('dynamodb', region_name=region)
    
    # Table name
    table_name = f"mowd-whisper-metadata-{env}"
    
    try:
        logger.info(f"Creating DynamoDB table {table_name}...")
        
        # Create table
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'lecture_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'lecture_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'school_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'SchoolIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'school_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'MOWD-Whisper'
                },
                {
                    'Key': 'Environment',
                    'Value': env
                }
            ]
        )
        
        logger.info(f"Successfully created DynamoDB table: {table_name}")
        logger.info("Waiting for table to become active...")
        
        # Wait for table to be created
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        return table_name
        
    except Exception as e:
        logger.error(f"Error creating DynamoDB table {table_name}: {e}")
        raise

def update_env_file(buckets, table_name, region, env):
    """
    Update .env file with AWS resource information
    
    Args:
        buckets: Dictionary with bucket names
        table_name: DynamoDB table name
        region: AWS region
        env: Environment name
    """
    env_file = Path('.env')
    
    if env_file.exists():
        # Read existing .env file
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update or add AWS settings
        settings = {
            'ENVIRONMENT': env,
            'STORAGE_MODE': 'aws',
            'AWS_REGION': region,
            'S3_LECTURE_BUCKET': buckets['audio_bucket'],
            'S3_TRANSCRIPT_BUCKET': buckets['transcript_bucket'],
            'DYNAMODB_TABLE': table_name
        }
        
        # Remove existing settings
        new_lines = []
        for line in lines:
            key = line.split('=')[0].strip() if '=' in line else ''
            if key not in settings:
                new_lines.append(line)
        
        # Add new settings
        for key, value in settings.items():
            new_lines.append(f"{key}={value}\n")
        
        # Write updated .env file
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
    else:
        # Create new .env file
        with open(env_file, 'w') as f:
            f.write(f"# Whisper MOWD Environment Configuration\n")
            f.write(f"# Updated by AWS setup script\n\n")
            f.write(f"ENVIRONMENT={env}\n")
            f.write(f"STORAGE_MODE=aws\n\n")
            f.write(f"# AWS Configuration\n")
            f.write(f"AWS_REGION={region}\n")
            f.write(f"S3_LECTURE_BUCKET={buckets['audio_bucket']}\n")
            f.write(f"S3_TRANSCRIPT_BUCKET={buckets['transcript_bucket']}\n")
            f.write(f"DYNAMODB_TABLE={table_name}\n\n")
            f.write(f"# Add your AWS credentials here or use AWS CLI configuration\n")
            f.write(f"# AWS_ACCESS_KEY_ID=your_access_key\n")
            f.write(f"# AWS_SECRET_ACCESS_KEY=your_secret_key\n\n")
            f.write(f"# Whisper Configuration\n")
            f.write(f"WHISPER_MODEL_SIZE=base\n\n")
            f.write(f"# Summarization Configuration\n")
            f.write(f"SUMMARIZER_TYPE=none\n")
    
    logger.info(f"Updated .env file with AWS resource information")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Set up AWS resources for Whisper MOWD")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"),
                        help="AWS region (default: from env or us-east-1)")
    parser.add_argument("--environment", default="dev", choices=["dev", "staging", "prod"],
                        help="Environment name (default: dev)")
    parser.add_argument("--terraform-state", action="store_true",
                        help="Create S3 bucket for Terraform state")
    parser.add_argument("--update-env", action="store_true",
                        help="Update .env file with resource information")
    
    args = parser.parse_args()
    
    try:
        print(f"Setting up AWS resources for Whisper MOWD in {args.region} ({args.environment})...")
        
        # Create S3 buckets
        buckets = setup_s3_buckets(args.region, args.environment, args.terraform_state)
        
        # Create DynamoDB table
        table_name = setup_dynamodb_table(args.region, args.environment)
        
        # Update .env file if requested
        if args.update_env:
            update_env_file(buckets, table_name, args.region, args.environment)
        
        print("\nAWS setup completed successfully!")
        print(f"Audio bucket: {buckets['audio_bucket']}")
        print(f"Transcript bucket: {buckets['transcript_bucket']}")
        if args.terraform_state:
            print(f"Terraform state bucket: {buckets['state_bucket']}")
        print(f"DynamoDB table: {table_name}")
        
        if not args.update_env:
            print("\nUpdate your .env file with these values or run with --update-env")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during AWS setup: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())