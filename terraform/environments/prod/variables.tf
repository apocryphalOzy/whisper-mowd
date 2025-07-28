# Production Environment Variables

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "security_email" {
  description = "Email address for security alerts"
  type        = string
  sensitive   = true
}

variable "monthly_budget_limit" {
  description = "Monthly AWS budget limit in USD"
  type        = string
  default     = "1000"
}

# Coturn Configuration
variable "coturn_instance_type" {
  description = "EC2 instance type for Coturn server"
  type        = string
  default     = "t3a.small"
}

variable "coturn_realm" {
  description = "TURN server realm"
  type        = string
  default     = "mowd-whisper.com"
}