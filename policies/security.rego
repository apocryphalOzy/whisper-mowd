package terraform

import future.keywords.contains
import future.keywords.if

# Critical security policies that must pass

# Deny unencrypted S3 buckets
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    not has_encryption(resource)
    msg := sprintf("S3 bucket '%s' must have encryption enabled", [resource.address])
}

# Deny S3 buckets without versioning
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_versioning"
    resource.change.after.versioning_configuration[_].status != "Enabled"
    msg := sprintf("S3 bucket versioning must be enabled for '%s'", [resource.address])
}

# Deny public S3 buckets
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_public_access_block"
    pab := resource.change.after
    not pab.block_public_acls
    msg := sprintf("S3 bucket '%s' must block public ACLs", [resource.address])
}

deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_public_access_block"
    pab := resource.change.after
    not pab.block_public_policy
    msg := sprintf("S3 bucket '%s' must block public policy", [resource.address])
}

# Deny KMS keys without rotation
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_kms_key"
    not resource.change.after.enable_key_rotation
    msg := sprintf("KMS key '%s' must have rotation enabled", [resource.address])
}

# Deny KMS keys with deletion window < 7 days
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_kms_key"
    resource.change.after.deletion_window_in_days < 7
    msg := sprintf("KMS key '%s' must have deletion window >= 7 days", [resource.address])
}

# Deny IAM policies with wildcard permissions
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_iam_role_policy"
    policy := json.unmarshal(resource.change.after.policy)
    statement := policy.Statement[_]
    statement.Effect == "Allow"
    action := statement.Action[_]
    contains(action, "*")
    msg := sprintf("IAM policy '%s' contains wildcard permissions", [resource.address])
}

# Deny Lambda functions without VPC
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_lambda_function"
    not resource.change.after.vpc_config
    msg := sprintf("Lambda function '%s' must be in VPC", [resource.address])
}

# Deny RDS without encryption
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_db_instance"
    not resource.change.after.storage_encrypted
    msg := sprintf("RDS instance '%s' must have encryption enabled", [resource.address])
}

# Deny security groups with unrestricted ingress
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_security_group_rule"
    resource.change.after.type == "ingress"
    resource.change.after.cidr_blocks[_] == "0.0.0.0/0"
    resource.change.after.from_port != 443
    msg := sprintf("Security group rule '%s' allows unrestricted access on non-HTTPS port", [resource.address])
}

# Deny ALB without TLS 1.2+
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_lb_listener"
    resource.change.after.protocol == "HTTPS"
    not startswith(resource.change.after.ssl_policy, "ELBSecurityPolicy-TLS13")
    not startswith(resource.change.after.ssl_policy, "ELBSecurityPolicy-TLS-1-2")
    msg := sprintf("ALB listener '%s' must use TLS 1.2 or higher", [resource.address])
}

# Deny Cognito without MFA
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_cognito_user_pool"
    resource.change.after.mfa_configuration != "ON"
    msg := sprintf("Cognito user pool '%s' must have MFA enabled", [resource.address])
}

# Deny DynamoDB without point-in-time recovery
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_dynamodb_table"
    not resource.change.after.point_in_time_recovery
    msg := sprintf("DynamoDB table '%s' must have point-in-time recovery enabled", [resource.address])
}

# Deny CloudWatch log groups without encryption
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_cloudwatch_log_group"
    not resource.change.after.kms_key_id
    msg := sprintf("CloudWatch log group '%s' must be encrypted with KMS", [resource.address])
}

# Deny secrets without rotation
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_secretsmanager_secret"
    not has_rotation(resource)
    msg := sprintf("Secret '%s' must have rotation enabled", [resource.address])
}

# Helper functions
has_encryption(resource) {
    resource.change.after.server_side_encryption_configuration
}

has_rotation(resource) {
    resource.change.after.rotation_rules
}

# Warnings (non-blocking)

warn[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_instance"
    not resource.change.after.monitoring
    msg := sprintf("EC2 instance '%s' should have detailed monitoring enabled", [resource.address])
}

warn[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    not has_lifecycle_rule(resource)
    msg := sprintf("S3 bucket '%s' should have lifecycle rules", [resource.address])
}

has_lifecycle_rule(resource) {
    resource.change.after.lifecycle_rule
}

# Summary function for CI/CD
summary = result {
    result := {
        "critical_violations": count(deny),
        "warnings": count(warn),
        "passed": count(deny) == 0
    }
}