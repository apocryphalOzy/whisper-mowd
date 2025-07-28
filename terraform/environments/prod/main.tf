# Production Environment Configuration

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket         = "mowd-whisper-terraform-state-prod"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "mowd-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = "prod"
      Project     = "MOWD-Whisper"
      ManagedBy   = "Terraform"
      CostCenter  = "Engineering"
      Compliance  = "HIPAA,GDPR"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Security Module
module "security" {
  source = "../../modules/security"
  
  environment = var.environment
  aws_region  = var.aws_region
  domain_name = var.domain_name
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"
  
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

# Authentication Module
module "auth" {
  source = "../../modules/auth"
  
  environment = var.environment
  domain_name = var.domain_name
  aws_region  = var.aws_region
}

# IAM Roles Module
module "iam" {
  source = "../../modules/iam"
  
  environment = var.environment
  aws_region  = var.aws_region
}

# S3 and Lifecycle Module
module "storage" {
  source = "../../modules/s3"
  
  environment = var.environment
}

# Logging Module
module "logging" {
  source = "../../modules/logging"
  
  environment = var.environment
}

# Monitoring Module
module "monitoring" {
  source = "../../modules/monitoring"
  
  environment    = var.environment
  security_email = var.security_email
}

# Lambda Functions
resource "aws_lambda_function" "transcribe" {
  filename         = "../../lambda/transcribe.zip"
  function_name    = "mowd-transcribe-${var.environment}"
  role            = module.iam.lambda_roles.transcribe
  handler         = "index.handler"
  source_code_hash = filebase64sha256("../../lambda/transcribe.zip")
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes
  memory_size     = 3008
  
  environment {
    variables = {
      AUDIO_BUCKET      = module.storage.bucket_names.audio
      TRANSCRIPT_BUCKET = module.storage.bucket_names.transcript
      KMS_KEY_ALIAS     = module.security.kms_key_aliases.transcript
      ENVIRONMENT       = var.environment
    }
  }
  
  vpc_config {
    subnet_ids         = module.vpc.private_subnet_ids
    security_group_ids = [module.vpc.security_group_ids.lambda]
  }
  
  tracing_config {
    mode = "Active"
  }
}

resource "aws_lambda_function" "summarize" {
  filename         = "../../lambda/summarize.zip"
  function_name    = "mowd-summarize-${var.environment}"
  role            = module.iam.lambda_roles.summarize
  handler         = "index.handler"
  source_code_hash = filebase64sha256("../../lambda/summarize.zip")
  runtime         = "python3.11"
  timeout         = 300  # 5 minutes
  memory_size     = 1024
  
  environment {
    variables = {
      TRANSCRIPT_BUCKET = module.storage.bucket_names.transcript
      SUMMARY_BUCKET    = module.storage.bucket_names.summary
      OPENAI_SECRET     = module.security.openai_secret_name
      ENVIRONMENT       = var.environment
    }
  }
  
  vpc_config {
    subnet_ids         = module.vpc.private_subnet_ids
    security_group_ids = [module.vpc.security_group_ids.lambda]
  }
}

resource "aws_lambda_function" "gdpr_delete" {
  filename         = "../../lambda/gdpr_delete.zip"
  function_name    = "mowd-gdpr-delete-${var.environment}"
  role            = module.iam.lambda_roles.gdpr_delete
  handler         = "deletion_handler.lambda_handler"
  source_code_hash = filebase64sha256("../../lambda/gdpr_delete.zip")
  runtime         = "python3.11"
  timeout         = 300
  
  environment {
    variables = {
      AUDIO_BUCKET      = module.storage.bucket_names.audio
      TRANSCRIPT_BUCKET = module.storage.bucket_names.transcript
      SUMMARY_BUCKET    = module.storage.bucket_names.summary
      METADATA_TABLE    = module.storage.dynamodb_table_name
      AUDIT_TABLE       = "${module.storage.dynamodb_table_name}-audit"
      ENVIRONMENT       = var.environment
    }
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "main" {
  name        = "mowd-api-${var.environment}"
  description = "MOWD Whisper API"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = var.environment
  
  depends_on = [
    aws_api_gateway_method.transcribe,
    aws_api_gateway_method.gdpr_delete
  ]
}

# API Gateway Methods (simplified)
resource "aws_api_gateway_resource" "transcribe" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "transcribe"
}

resource "aws_api_gateway_method" "transcribe" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.transcribe.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_resource" "gdpr" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "gdpr"
}

resource "aws_api_gateway_resource" "gdpr_delete" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.gdpr.id
  path_part   = "delete"
}

resource "aws_api_gateway_method" "gdpr_delete" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.gdpr_delete.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_authorizer" "cognito" {
  name            = "mowd-cognito-authorizer-${var.environment}"
  rest_api_id     = aws_api_gateway_rest_api.main.id
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [module.auth.user_pool_arn]
  identity_source = "method.request.header.Authorization"
}

# WAF for API Gateway
resource "aws_wafv2_web_acl" "api" {
  name  = "mowd-api-waf-${var.environment}"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  rule {
    name     = "RateLimitRule"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }
  
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSet"
      sampled_requests_enabled   = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "mowd-api-waf"
    sampled_requests_enabled   = true
  }
}

resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = aws_api_gateway_stage.main.arn
  web_acl_arn  = aws_wafv2_web_acl.api.arn
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/mowd-${var.environment}"
  retention_in_days = 30
  kms_key_id        = module.security.kms_key_arns.logs
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "MOWD Whisper CDN ${var.environment}"
  default_root_object = "index.html"
  aliases             = [var.domain_name]
  price_class         = "PriceClass_100"
  
  origin {
    domain_name = aws_api_gateway_rest_api.main.id
    origin_id   = "api-gateway"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2", "TLSv1.3"]
    }
  }
  
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "api-gateway"
    
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type"]
      
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    acm_certificate_arn      = module.security.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

# Budget Alert
resource "aws_budgets_budget" "monthly" {
  name         = "mowd-monthly-budget-${var.environment}"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "FORECASTED"
    subscriber_email_addresses = [var.security_email]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = [var.security_email]
  }
}