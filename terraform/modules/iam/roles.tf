# Lambda Execution Roles with Least Privilege

# Transcription Lambda Role
resource "aws_iam_role" "lambda_transcribe" {
  name = "mowd-lambda-transcribe-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
  
  tags = {
    Name        = "mowd-lambda-transcribe-${var.environment}"
    Environment = var.environment
    Purpose     = "audio-transcription"
  }
}

# Transcription Lambda Policy
resource "aws_iam_role_policy" "lambda_transcribe" {
  name = "transcribe-policy"
  role = aws_iam_role.lambda_transcribe.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 Read Audio
      {
        Sid    = "ReadAudioFiles"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.audio.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      # S3 Write Transcripts
      {
        Sid    = "WriteTranscripts"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.transcript.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.transcript.arn
          }
        }
      },
      # KMS Decrypt Audio
      {
        Sid    = "DecryptAudio"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.audio.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${var.aws_region}.amazonaws.com"
          }
        }
      },
      # KMS Encrypt Transcripts
      {
        Sid    = "EncryptTranscripts"
        Effect = "Allow"
        Action = [
          "kms:GenerateDataKey",
          "kms:Decrypt"
        ]
        Resource = aws_kms_key.transcript.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${var.aws_region}.amazonaws.com"
          }
        }
      },
      # DynamoDB Write
      {
        Sid    = "UpdateMetadata"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.metadata.arn
        Condition = {
          StringEquals = {
            "dynamodb:LeadingKeys" = "$${aws:userid}"
          }
        }
      },
      # CloudWatch Logs
      {
        Sid    = "WriteLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/mowd-transcribe-*"
      },
      # X-Ray Tracing
      {
        Sid    = "XRayTracing"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

# Summarization Lambda Role
resource "aws_iam_role" "lambda_summarize" {
  name = "mowd-lambda-summarize-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
  
  tags = {
    Name        = "mowd-lambda-summarize-${var.environment}"
    Environment = var.environment
    Purpose     = "text-summarization"
  }
}

# Summarization Lambda Policy
resource "aws_iam_role_policy" "lambda_summarize" {
  name = "summarize-policy"
  role = aws_iam_role.lambda_summarize.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 Read Transcripts
      {
        Sid    = "ReadTranscripts"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.transcript.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      # S3 Write Summaries
      {
        Sid    = "WriteSummaries"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.summary.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.summary.arn
          }
        }
      },
      # KMS Operations
      {
        Sid    = "KMSOperations"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
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
      },
      # Secrets Manager for API Keys
      {
        Sid    = "GetAPIKeys"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.openai_api_key.arn
        Condition = {
          StringEquals = {
            "secretsmanager:VersionStage" = "AWSCURRENT"
          }
        }
      },
      # DynamoDB Update
      {
        Sid    = "UpdateMetadata"
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.metadata.arn
      },
      # CloudWatch Logs
      {
        Sid    = "WriteLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/mowd-summarize-*"
      }
    ]
  })
}

# GDPR Deletion Lambda Role
resource "aws_iam_role" "lambda_gdpr_delete" {
  name = "mowd-lambda-gdpr-delete-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  
  tags = {
    Name        = "mowd-lambda-gdpr-delete-${var.environment}"
    Environment = var.environment
    Purpose     = "gdpr-compliance"
  }
}

# GDPR Deletion Policy
resource "aws_iam_role_policy" "lambda_gdpr_delete" {
  name = "gdpr-delete-policy"
  role = aws_iam_role.lambda_gdpr_delete.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 Delete Operations
      {
        Sid    = "DeleteS3Objects"
        Effect = "Allow"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion",
          "s3:ListBucket",
          "s3:ListBucketVersions"
        ]
        Resource = [
          aws_s3_bucket.audio.arn,
          "${aws_s3_bucket.audio.arn}/*",
          aws_s3_bucket.transcript.arn,
          "${aws_s3_bucket.transcript.arn}/*",
          aws_s3_bucket.summary.arn,
          "${aws_s3_bucket.summary.arn}/*"
        ]
      },
      # DynamoDB Delete
      {
        Sid    = "DeleteMetadata"
        Effect = "Allow"
        Action = [
          "dynamodb:DeleteItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.metadata.arn,
          "${aws_dynamodb_table.metadata.arn}/index/*"
        ]
      },
      # CloudWatch Logs
      {
        Sid    = "WriteLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/mowd-gdpr-*"
      },
      # Audit Trail
      {
        Sid    = "AuditDeletion"
        Effect = "Allow"
        Action = [
          "cloudtrail:LookupEvents",
          "cloudtrail:PutEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# API Gateway Execution Role
resource "aws_iam_role" "api_gateway" {
  name = "mowd-api-gateway-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  
  tags = {
    Name        = "mowd-api-gateway-${var.environment}"
    Environment = var.environment
  }
}

# API Gateway Policy
resource "aws_iam_role_policy" "api_gateway" {
  name = "api-gateway-policy"
  role = aws_iam_role.api_gateway.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.transcribe.arn,
          aws_lambda_function.summarize.arn,
          aws_lambda_function.gdpr_delete.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apigateway/*"
      }
    ]
  })
}

# Explicit Deny Policies
resource "aws_iam_policy" "explicit_deny" {
  name        = "mowd-explicit-deny-${var.environment}"
  description = "Explicit deny for sensitive operations"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Action = "s3:PutObject"
        Resource = [
          "${aws_s3_bucket.audio.arn}/*",
          "${aws_s3_bucket.transcript.arn}/*",
          "${aws_s3_bucket.summary.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid    = "DenyNonSecureTransport"
        Effect = "Deny"
        Action = "*"
        Resource = "*"
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "DenyRootAccountUsage"
        Effect = "Deny"
        Action = "*"
        Resource = "*"
        Condition = {
          StringLike = {
            "aws:userid" = "AIDAI*"
          }
        }
      }
    ]
  })
}

# Attach explicit deny to all roles
resource "aws_iam_role_policy_attachment" "explicit_deny_transcribe" {
  role       = aws_iam_role.lambda_transcribe.name
  policy_arn = aws_iam_policy.explicit_deny.arn
}

resource "aws_iam_role_policy_attachment" "explicit_deny_summarize" {
  role       = aws_iam_role.lambda_summarize.name
  policy_arn = aws_iam_policy.explicit_deny.arn
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

# Outputs
output "lambda_roles" {
  value = {
    transcribe  = aws_iam_role.lambda_transcribe.arn
    summarize   = aws_iam_role.lambda_summarize.arn
    gdpr_delete = aws_iam_role.lambda_gdpr_delete.arn
  }
}

output "api_gateway_role" {
  value = aws_iam_role.api_gateway.arn
}