# S3 Lifecycle Policies for Data Retention

# Audio Bucket with 30-day deletion
resource "aws_s3_bucket" "audio" {
  bucket = "mowd-audio-${var.environment}-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "mowd-audio-${var.environment}"
    Environment = var.environment
    DataType    = "audio"
    Compliance  = "HIPAA,GDPR"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audio" {
  bucket = aws_s3_bucket.audio.id
  
  rule {
    id     = "delete-raw-audio"
    status = "Enabled"
    
    filter {
      prefix = "lectures/"
    }
    
    transition {
      days          = 7
      storage_class = "GLACIER_IR"
    }
    
    expiration {
      days = 30  # Delete raw audio after 30 days
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
  
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Transcript Bucket with academic year + 1 retention
resource "aws_s3_bucket" "transcript" {
  bucket = "mowd-transcripts-${var.environment}-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "mowd-transcripts-${var.environment}"
    Environment = var.environment
    DataType    = "transcript"
    Compliance  = "HIPAA,GDPR"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "transcript" {
  bucket = aws_s3_bucket.transcript.id
  
  rule {
    id     = "archive-old-transcripts"
    status = "Enabled"
    
    filter {
      prefix = "transcripts/"
    }
    
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 365
      storage_class = "GLACIER"
    }
    
    # Academic year + 1 = ~18 months
    expiration {
      days = 548
    }
  }
}

# Summary Bucket (same retention as transcripts)
resource "aws_s3_bucket" "summary" {
  bucket = "mowd-summaries-${var.environment}-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "mowd-summaries-${var.environment}"
    Environment = var.environment
    DataType    = "summary"
    Compliance  = "HIPAA,GDPR"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "summary" {
  bucket = aws_s3_bucket.summary.id
  
  rule {
    id     = "archive-old-summaries"
    status = "Enabled"
    
    filter {
      prefix = "summaries/"
    }
    
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 365
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 548  # Same as transcripts
    }
  }
}

# Enable versioning for all buckets
resource "aws_s3_bucket_versioning" "audio" {
  bucket = aws_s3_bucket.audio.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "transcript" {
  bucket = aws_s3_bucket.transcript.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "summary" {
  bucket = aws_s3_bucket.summary.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Object Lock for compliance
resource "aws_s3_bucket_object_lock_configuration" "audio" {
  bucket = aws_s3_bucket.audio.id
  
  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 7
    }
  }
}

# Event notifications for lifecycle events
resource "aws_s3_bucket_notification" "audio_deletion" {
  bucket = aws_s3_bucket.audio.id
  
  eventbridge = true
}

# EventBridge rule for audio deletion
resource "aws_cloudwatch_event_rule" "audio_deletion" {
  name        = "mowd-audio-deletion-${var.environment}"
  description = "Capture S3 object deletion events"
  
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Deleted"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.audio.id]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "audit_deletion" {
  rule      = aws_cloudwatch_event_rule.audio_deletion.name
  target_id = "AuditDeletion"
  arn       = aws_lambda_function.audit_logger.arn
}

# DynamoDB TTL for metadata
resource "aws_dynamodb_table" "metadata" {
  name           = "mowd-metadata-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "lecture_id"
  
  attribute {
    name = "lecture_id"
    type = "S"
  }
  
  attribute {
    name = "school_id"
    type = "S"
  }
  
  attribute {
    name = "ttl"
    type = "N"
  }
  
  # TTL configuration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  # Global secondary index for school queries
  global_secondary_index {
    name            = "SchoolIndex"
    hash_key        = "school_id"
    projection_type = "ALL"
  }
  
  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }
  
  # Encryption
  server_side_encryption {
    enabled = true
  }
  
  tags = {
    Name        = "mowd-metadata-${var.environment}"
    Environment = var.environment
  }
}

# Backup configuration
resource "aws_backup_plan" "data_backup" {
  name = "mowd-backup-plan-${var.environment}"
  
  rule {
    rule_name         = "daily_backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 5 ? * * *)"  # Daily at 5 AM UTC
    
    lifecycle {
      delete_after = 35  # Keep backups for 35 days
    }
    
    recovery_point_tags = {
      Environment = var.environment
      BackupType  = "scheduled"
    }
  }
  
  rule {
    rule_name         = "weekly_backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 5 ? * SUN *)"  # Weekly on Sunday
    
    lifecycle {
      delete_after       = 90
      cold_storage_after = 30
    }
  }
}

resource "aws_backup_vault" "main" {
  name        = "mowd-backup-vault-${var.environment}"
  kms_key_arn = aws_kms_key.backup.arn
  
  tags = {
    Name        = "mowd-backup-vault-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_backup_selection" "data" {
  name         = "mowd-backup-selection-${var.environment}"
  plan_id      = aws_backup_plan.data_backup.id
  iam_role_arn = aws_iam_role.backup.arn
  
  resources = [
    aws_dynamodb_table.metadata.arn
  ]
  
  selection_tag {
    type  = "STRINGEQUALS"
    key   = "Environment"
    value = var.environment
  }
}

# IAM role for backup
resource "aws_iam_role" "backup" {
  name = "mowd-backup-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# KMS key for backups
resource "aws_kms_key" "backup" {
  description             = "KMS key for backup encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    Name        = "mowd-backup-kms-${var.environment}"
    Environment = var.environment
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
}

# Outputs
output "bucket_names" {
  value = {
    audio      = aws_s3_bucket.audio.id
    transcript = aws_s3_bucket.transcript.id
    summary    = aws_s3_bucket.summary.id
  }
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.metadata.name
}

output "backup_vault_name" {
  value = aws_backup_vault.main.name
}