# Cognito User Pool for Authentication

resource "aws_cognito_user_pool" "main" {
  name = "mowd-users-${var.environment}"
  
  # Password Policy
  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 1
  }
  
  # MFA Configuration
  mfa_configuration = "ON"
  
  software_token_mfa_configuration {
    enabled = true
  }
  
  # Account Recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
  
  # User Attributes
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = false
    developer_only_attribute = false
    
    string_attribute_constraints {
      min_length = 5
      max_length = 256
    }
  }
  
  schema {
    name                     = "school_id"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false
    
    string_attribute_constraints {
      min_length = 1
      max_length = 128
    }
  }
  
  schema {
    name                     = "role"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false
    
    string_attribute_constraints {
      min_length = 1
      max_length = 50
    }
  }
  
  # Username Configuration
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  
  # Security Features
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }
  
  # Device Tracking
  device_configuration {
    challenge_required_on_new_device      = true
    device_only_remembered_on_user_prompt = true
  }
  
  # Email Configuration
  email_configuration {
    email_sending_account = "DEVELOPER"
    from_email_address    = "noreply@${var.domain_name}"
    source_arn            = aws_ses_email_identity.noreply.arn
  }
  
  # Lambda Triggers
  lambda_config {
    pre_sign_up        = aws_lambda_function.pre_signup.arn
    post_confirmation  = aws_lambda_function.post_confirmation.arn
    pre_authentication = aws_lambda_function.pre_authentication.arn
    custom_message     = aws_lambda_function.custom_message.arn
  }
  
  # Deletion Protection
  deletion_protection = var.environment == "prod" ? "ACTIVE" : "INACTIVE"
  
  tags = {
    Name        = "mowd-user-pool-${var.environment}"
    Environment = var.environment
    Compliance  = "HIPAA,GDPR"
  }
}

# App Client
resource "aws_cognito_user_pool_client" "web_app" {
  name                                 = "mowd-web-client-${var.environment}"
  user_pool_id                         = aws_cognito_user_pool.main.id
  generate_secret                      = false
  refresh_token_validity               = 30
  access_token_validity                = 15  # 15 minutes
  id_token_validity                    = 15  # 15 minutes
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
  
  # OAuth Configuration
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  callback_urls                        = ["https://${var.domain_name}/auth/callback"]
  logout_urls                          = ["https://${var.domain_name}/auth/logout"]
  supported_identity_providers         = ["COGNITO"]
  
  # Token Configuration
  read_attributes = [
    "email",
    "email_verified",
    "custom:school_id",
    "custom:role"
  ]
  
  write_attributes = [
    "email",
    "custom:school_id",
    "custom:role"
  ]
  
  # Security
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
  
  # Advanced Security
  enable_propagate_additional_user_context_data = true
}

# Domain for Hosted UI (if needed)
resource "aws_cognito_user_pool_domain" "main" {
  domain          = "mowd-auth-${var.environment}"
  user_pool_id    = aws_cognito_user_pool.main.id
  certificate_arn = aws_acm_certificate.auth.arn
}

# Identity Pool for AWS Credentials
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "mowd-identity-${var.environment}"
  allow_unauthenticated_identities = false
  allow_classic_flow               = false
  
  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.web_app.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = true
  }
  
  tags = {
    Name        = "mowd-identity-pool-${var.environment}"
    Environment = var.environment
  }
}

# IAM Roles for Identity Pool
resource "aws_iam_role" "authenticated" {
  name = "mowd-cognito-authenticated-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })
  
  tags = {
    Name        = "mowd-cognito-authenticated-${var.environment}"
    Environment = var.environment
  }
}

# Attach Policy to Authenticated Role
resource "aws_iam_role_policy" "authenticated" {
  name = "mowd-cognito-authenticated-policy"
  role = aws_iam_role.authenticated.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.transcript.arn}/*",
          "${aws_s3_bucket.summary.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [
          aws_kms_key.transcript.arn,
          aws_kms_key.summary.arn
        ]
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Identity Pool Role Attachment
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id
  
  roles = {
    authenticated = aws_iam_role.authenticated.arn
  }
  
  role_mapping {
    identity_provider         = "${aws_cognito_user_pool.main.endpoint}:${aws_cognito_user_pool_client.web_app.id}"
    ambiguous_role_resolution = "AuthenticatedRole"
    type                      = "Token"
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "failed_sign_in" {
  alarm_name          = "cognito-failed-signin-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "UserAuthenticationFailure"
  namespace           = "AWS/Cognito"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert on multiple failed sign-in attempts"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  dimensions = {
    UserPool = aws_cognito_user_pool.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "account_takeover" {
  alarm_name          = "cognito-account-takeover-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "AccountTakeoverRisk"
  namespace           = "AWS/Cognito"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert on account takeover risk"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  dimensions = {
    UserPool = aws_cognito_user_pool.main.id
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# Outputs
output "user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.web_app.id
}

output "identity_pool_id" {
  value = aws_cognito_identity_pool.main.id
}

output "user_pool_domain" {
  value = aws_cognito_user_pool_domain.main.domain
}