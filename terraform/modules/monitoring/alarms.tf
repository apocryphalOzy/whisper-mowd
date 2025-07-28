# CloudWatch Alarms for Security Monitoring

# SNS Topic for Security Alerts
resource "aws_sns_topic" "security_alerts" {
  name              = "mowd-security-alerts-${var.environment}"
  kms_master_key_id = aws_kms_key.sns.id
  
  tags = {
    Name        = "mowd-security-alerts-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "security_email" {
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = "email"
  endpoint  = var.security_email
}

resource "aws_sns_topic_subscription" "security_slack" {
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.slack_notifier.arn
}

# KMS Key for SNS
resource "aws_kms_key" "sns" {
  description             = "KMS key for SNS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    Name        = "mowd-sns-kms-${var.environment}"
    Environment = var.environment
  }
}

# Sample Alarm 1: Unauthorized KMS Key Access
resource "aws_cloudwatch_log_metric_filter" "unauthorized_kms_access" {
  name           = "unauthorized-kms-access-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  pattern        = <<-EOT
    {
      ($.eventName = "Decrypt" || $.eventName = "GenerateDataKey" || $.eventName = "CreateGrant") &&
      $.errorCode = "*UnauthorizedOperation*" &&
      $.userIdentity.arn != "arn:aws:sts::*:assumed-role/mowd-*"
    }
  EOT
  
  metric_transformation {
    name      = "UnauthorizedKMSAccess"
    namespace = "MOWD/Security"
    value     = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "unauthorized_kms_access" {
  alarm_name          = "mowd-unauthorized-kms-access-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "UnauthorizedKMSAccess"
  namespace           = "MOWD/Security"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert on unauthorized KMS key access attempts"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  tags = {
    Name        = "mowd-unauthorized-kms-access-${var.environment}"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# Sample Alarm 2: Mass Data Download Detection
resource "aws_cloudwatch_log_metric_filter" "mass_download" {
  name           = "mass-download-detection-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  pattern        = <<-EOT
    {
      $.eventName = "GetObject" &&
      $.requestParameters.bucketName = "mowd-*"
    }
  EOT
  
  metric_transformation {
    name      = "S3Downloads"
    namespace = "MOWD/Security"
    value     = "1"
    default_value = "0"
    
    dimensions = {
      UserIdentity = "$.userIdentity.arn"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "mass_download" {
  alarm_name          = "mowd-mass-download-detection-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "S3Downloads"
  namespace           = "MOWD/Security"
  period              = "3600"  # 1 hour
  statistic           = "Sum"
  threshold           = "1000"  # More than 1000 downloads per hour
  alarm_description   = "Alert on mass data download (>1000 objects/hour)"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  treat_missing_data  = "notBreaching"
  
  tags = {
    Name        = "mowd-mass-download-detection-${var.environment}"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# Additional Security Alarms

# Root Account Usage
resource "aws_cloudwatch_log_metric_filter" "root_account_usage" {
  name           = "root-account-usage-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  pattern        = <<-EOT
    {
      $.userIdentity.type = "Root" &&
      $.userIdentity.invokedBy NOT EXISTS &&
      $.eventType != "AwsServiceEvent"
    }
  EOT
  
  metric_transformation {
    name      = "RootAccountUsage"
    namespace = "MOWD/Security"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "root_account_usage" {
  alarm_name          = "mowd-root-account-usage-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "RootAccountUsage"
  namespace           = "MOWD/Security"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert on root account usage"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
}

# IAM Policy Changes
resource "aws_cloudwatch_log_metric_filter" "iam_policy_changes" {
  name           = "iam-policy-changes-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name
  pattern        = <<-EOT
    {
      ($.eventName = "DeleteGroupPolicy" || $.eventName = "DeleteRolePolicy" ||
       $.eventName = "DeleteUserPolicy" || $.eventName = "PutGroupPolicy" ||
       $.eventName = "PutRolePolicy" || $.eventName = "PutUserPolicy" ||
       $.eventName = "CreatePolicy" || $.eventName = "DeletePolicy" ||
       $.eventName = "CreatePolicyVersion" || $.eventName = "DeletePolicyVersion" ||
       $.eventName = "AttachRolePolicy" || $.eventName = "DetachRolePolicy" ||
       $.eventName = "AttachUserPolicy" || $.eventName = "DetachUserPolicy" ||
       $.eventName = "AttachGroupPolicy" || $.eventName = "DetachGroupPolicy")
    }
  EOT
  
  metric_transformation {
    name      = "IAMPolicyChanges"
    namespace = "MOWD/Security"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "iam_policy_changes" {
  alarm_name          = "mowd-iam-policy-changes-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "IAMPolicyChanges"
  namespace           = "MOWD/Security"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert on IAM policy changes"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
}

# Failed Authentication Attempts
resource "aws_cloudwatch_log_metric_filter" "failed_auth" {
  name           = "failed-authentication-${var.environment}"
  log_group_name = "/aws/lambda/mowd-auth-${var.environment}"
  pattern        = '[timestamp, request_id, event_type="AUTHENTICATION_FAILED"]'
  
  metric_transformation {
    name      = "FailedAuthentications"
    namespace = "MOWD/Security"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "failed_auth" {
  alarm_name          = "mowd-failed-authentication-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FailedAuthentications"
  namespace           = "MOWD/Security"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert on multiple failed authentication attempts"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
}

# Lambda Error Rate
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = {
    transcribe = "mowd-transcribe-${var.environment}"
    summarize  = "mowd-summarize-${var.environment}"
  }
  
  alarm_name          = "mowd-lambda-errors-${each.key}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert on high Lambda error rate"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  dimensions = {
    FunctionName = each.value
  }
}

# Cost Anomaly Detection
resource "aws_cloudwatch_anomaly_detector" "cost" {
  metric_name = "EstimatedCharges"
  namespace   = "AWS/Billing"
  stat        = "Maximum"
  
  dimensions = {
    Currency = "USD"
  }
}

resource "aws_cloudwatch_metric_alarm" "cost_anomaly" {
  alarm_name          = "mowd-cost-anomaly-${var.environment}"
  comparison_operator = "LessThanLowerOrGreaterThanUpperThreshold"
  evaluation_periods  = "2"
  threshold_metric_id = "ad1"
  alarm_description   = "Alert on cost anomalies"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  metric_query {
    id          = "m1"
    return_data = true
    
    metric {
      metric_name = "EstimatedCharges"
      namespace   = "AWS/Billing"
      period      = "86400"
      stat        = "Maximum"
      
      dimensions = {
        Currency = "USD"
      }
    }
  }
  
  metric_query {
    id          = "ad1"
    expression  = "ANOMALY_DETECTION_BAND(m1, 2)"
  }
}

# Sample CloudWatch Insights Query
resource "aws_cloudwatch_query_definition" "suspicious_activity" {
  name = "MOWD-Suspicious-Activity-${var.environment}"
  
  log_group_names = [
    aws_cloudwatch_log_group.cloudtrail.name,
    "/aws/lambda/mowd-*"
  ]
  
  query_string = <<-EOQ
    fields @timestamp, userIdentity.arn, sourceIPAddress, eventName, errorCode
    | filter errorCode like /Unauthorized|Denied|Forbidden/
    | stats count(*) as failed_attempts by userIdentity.arn, sourceIPAddress
    | filter failed_attempts > 5
    | sort failed_attempts desc
  EOQ
}

# Application Logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/mowd/application/${var.environment}"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.logs.arn
  
  tags = {
    Name        = "mowd-app-logs-${var.environment}"
    Environment = var.environment
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "security_email" {
  description = "Email for security alerts"
  type        = string
}

# Outputs
output "sns_topic_arn" {
  value = aws_sns_topic.security_alerts.arn
}

output "log_group_names" {
  value = {
    cloudtrail = aws_cloudwatch_log_group.cloudtrail.name
    app_logs   = aws_cloudwatch_log_group.app_logs.name
  }
}