# CloudTrail Lake for Advanced Audit Logging

resource "aws_cloudtrail_event_data_store" "main" {
  name                           = "mowd-cloudtrail-lake-${var.environment}"
  retention_period               = 90  # 90 days retention
  multi_region_enabled           = true
  organization_enabled           = false
  termination_protection_enabled = var.environment == "prod" ? true : false
  
  advanced_event_selector {
    name = "Log all S3 data events"
    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }
    field_selector {
      field  = "resources.type"
      equals = ["AWS::S3::Object"]
    }
    field_selector {
      field           = "resources.ARN"
      starts_with     = ["arn:aws:s3:::mowd-"]
    }
  }
  
  advanced_event_selector {
    name = "Log all management events"
    field_selector {
      field  = "eventCategory"
      equals = ["Management"]
    }
  }
  
  advanced_event_selector {
    name = "Log DynamoDB data events"
    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }
    field_selector {
      field  = "resources.type"
      equals = ["AWS::DynamoDB::Table"]
    }
  }
  
  tags = {
    Name        = "mowd-cloudtrail-lake-${var.environment}"
    Environment = var.environment
    Compliance  = "HIPAA,GDPR"
  }
}

# Traditional CloudTrail for Backup
resource "aws_cloudtrail" "main" {
  name                          = "mowd-cloudtrail-${var.environment}"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_logging                = true
  kms_key_id                    = aws_kms_key.cloudtrail.arn
  
  event_selector {
    read_write_type           = "All"
    include_management_events = true
    
    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::mowd-*/"]
    }
    
    data_resource {
      type   = "AWS::DynamoDB::Table"
      values = ["arn:aws:dynamodb:*:*:table/mowd-*"]
    }
  }
  
  insight_selector {
    insight_type = "ApiCallRateInsight"
  }
  
  insight_selector {
    insight_type = "ApiErrorRateInsight"
  }
  
  tags = {
    Name        = "mowd-cloudtrail-${var.environment}"
    Environment = var.environment
  }
}

# S3 Bucket for CloudTrail
resource "aws_s3_bucket" "cloudtrail" {
  bucket = "mowd-cloudtrail-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "mowd-cloudtrail-logs-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.cloudtrail.arn
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  
  rule {
    id     = "expire-old-logs"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_policy" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail.arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      }
    ]
  })
}

# KMS Key for CloudTrail
resource "aws_kms_key" "cloudtrail" {
  description             = "KMS key for CloudTrail logs"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudTrail to encrypt logs"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = {
    Name        = "mowd-cloudtrail-kms-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "cloudtrail" {
  name          = "alias/mowd-cloudtrail-${var.environment}"
  target_key_id = aws_kms_key.cloudtrail.key_id
}

# GuardDuty for Threat Detection
resource "aws_guardduty_detector" "main" {
  enable = true
  
  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = false
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }
  
  tags = {
    Name        = "mowd-guardduty-${var.environment}"
    Environment = var.environment
  }
}

# GuardDuty findings to CloudWatch Events
resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "mowd-guardduty-findings-${var.environment}"
  description = "Capture GuardDuty findings"
  
  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [
        { numeric = [">", 3] }  # Medium severity and above
      ]
    }
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.security_alerts.arn
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
}

# Outputs
output "cloudtrail_name" {
  value = aws_cloudtrail.main.name
}

output "cloudtrail_lake_arn" {
  value = aws_cloudtrail_event_data_store.main.arn
}

output "guardduty_detector_id" {
  value = aws_guardduty_detector.main.id
}