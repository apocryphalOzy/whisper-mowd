# KMS Keys for Data Encryption

resource "aws_kms_key" "audio" {
  description             = "KMS key for audio file encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    Name        = "mowd-audio-kms-${var.environment}"
    Environment = var.environment
    Purpose     = "audio-encryption"
    Compliance  = "HIPAA,GDPR"
  }
}

resource "aws_kms_key" "transcript" {
  description             = "KMS key for transcript encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    Name        = "mowd-transcript-kms-${var.environment}"
    Environment = var.environment
    Purpose     = "transcript-encryption"
    Compliance  = "HIPAA,GDPR"
  }
}

resource "aws_kms_key" "summary" {
  description             = "KMS key for summary encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    Name        = "mowd-summary-kms-${var.environment}"
    Environment = var.environment
    Purpose     = "summary-encryption"
    Compliance  = "HIPAA,GDPR"
  }
}

# KMS Aliases for key rotation
resource "aws_kms_alias" "audio" {
  name          = "alias/mowd-audio-${var.environment}"
  target_key_id = aws_kms_key.audio.key_id
}

resource "aws_kms_alias" "transcript" {
  name          = "alias/mowd-transcript-${var.environment}"
  target_key_id = aws_kms_key.transcript.key_id
}

resource "aws_kms_alias" "summary" {
  name          = "alias/mowd-summary-${var.environment}"
  target_key_id = aws_kms_key.summary.key_id
}

# Key Policies
data "aws_iam_policy_document" "kms_policy" {
  statement {
    sid    = "Enable IAM User Permissions"
    effect = "Allow"
    
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    
    actions   = ["kms:*"]
    resources = ["*"]
  }
  
  statement {
    sid    = "Allow Lambda Functions"
    effect = "Allow"
    
    principals {
      type = "AWS"
      identifiers = [
        aws_iam_role.lambda_transcribe.arn,
        aws_iam_role.lambda_summarize.arn
      ]
    }
    
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
      "kms:CreateGrant"
    ]
    
    resources = ["*"]
    
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["s3.${var.aws_region}.amazonaws.com"]
    }
  }
  
  statement {
    sid    = "Deny Unencrypted Access"
    effect = "Deny"
    
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    
    actions   = ["kms:*"]
    resources = ["*"]
    
    condition {
      test     = "Bool"
      variable = "kms:EncryptionContext:aws:s3:arn"
      values   = ["false"]
    }
  }
  
  statement {
    sid    = "CloudTrail Logging"
    effect = "Allow"
    
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    
    actions = [
      "kms:GenerateDataKey",
      "kms:DescribeKey"
    ]
    
    resources = ["*"]
  }
}

resource "aws_kms_key_policy" "audio" {
  key_id = aws_kms_key.audio.id
  policy = data.aws_iam_policy_document.kms_policy.json
}

resource "aws_kms_key_policy" "transcript" {
  key_id = aws_kms_key.transcript.id
  policy = data.aws_iam_policy_document.kms_policy.json
}

resource "aws_kms_key_policy" "summary" {
  key_id = aws_kms_key.summary.id
  policy = data.aws_iam_policy_document.kms_policy.json
}

# CloudWatch Alarms for KMS
resource "aws_cloudwatch_metric_alarm" "kms_key_deletion" {
  for_each = {
    audio      = aws_kms_key.audio.id
    transcript = aws_kms_key.transcript.id
    summary    = aws_kms_key.summary.id
  }
  
  alarm_name          = "kms-key-deletion-${each.key}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "NumberOfOperations"
  namespace           = "AWS/KMS"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert on KMS key deletion attempts"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  dimensions = {
    KeyId     = each.value
    Operation = "ScheduleKeyDeletion"
  }
}

# TLS Certificate for ALB
resource "aws_acm_certificate" "main" {
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"
  
  tags = {
    Name        = "mowd-certificate-${var.environment}"
    Environment = var.environment
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# ALB Security Policy for TLS 1.3
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# S3 Bucket Encryption Configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "audio" {
  bucket = aws_s3_bucket.audio.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.audio.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "transcript" {
  bucket = aws_s3_bucket.transcript.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.transcript.arn
    }
    bucket_key_enabled = true
  }
}

# Secrets Manager for API Keys
resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "mowd/openai-api-key/${var.environment}"
  description             = "OpenAI API key for summarization"
  recovery_window_in_days = 7
  
  tags = {
    Name        = "openai-api-key-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_rotation" "openai_api_key" {
  secret_id = aws_secretsmanager_secret.openai_api_key.id
  
  rotation_rules {
    automatically_after_days = 90
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "domain_name" {
  description = "Domain name for TLS certificate"
  type        = string
}

# Outputs
output "kms_key_arns" {
  value = {
    audio      = aws_kms_key.audio.arn
    transcript = aws_kms_key.transcript.arn
    summary    = aws_kms_key.summary.arn
  }
}

output "kms_key_aliases" {
  value = {
    audio      = aws_kms_alias.audio.name
    transcript = aws_kms_alias.transcript.name
    summary    = aws_kms_alias.summary.name
  }
}