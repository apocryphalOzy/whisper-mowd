# VPC Configuration with Security-First Design

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name        = "mowd-vpc-${var.environment}"
    Environment = var.environment
  }
}

# Private Subnets for Lambda Functions
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone = var.availability_zones[count.index]
  
  tags = {
    Name        = "mowd-private-${var.availability_zones[count.index]}-${var.environment}"
    Environment = var.environment
    Type        = "private"
  }
}

# Public Subnets for NAT Gateways Only
resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false
  
  tags = {
    Name        = "mowd-public-${var.availability_zones[count.index]}-${var.environment}"
    Environment = var.environment
    Type        = "public"
  }
}

# Internet Gateway (for NAT only)
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name        = "mowd-igw-${var.environment}"
    Environment = var.environment
  }
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"
  
  tags = {
    Name        = "mowd-nat-eip-${count.index}-${var.environment}"
    Environment = var.environment
  }
  
  depends_on = [aws_internet_gateway.main]
}

# NAT Gateways
resource "aws_nat_gateway" "main" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  
  tags = {
    Name        = "mowd-nat-${var.availability_zones[count.index]}-${var.environment}"
    Environment = var.environment
  }
  
  depends_on = [aws_internet_gateway.main]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name        = "mowd-public-rt-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }
  
  tags = {
    Name        = "mowd-private-rt-${count.index}-${var.environment}"
    Environment = var.environment
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# S3 VPC Endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          "arn:aws:s3:::mowd-*/*",
          "arn:aws:s3:::mowd-*"
        ]
        Condition = {
          StringEquals = {
            "aws:PrincipalAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
  
  tags = {
    Name        = "mowd-s3-endpoint-${var.environment}"
    Environment = var.environment
  }
}

# DynamoDB VPC Endpoint
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "dynamodb:*"
        Resource  = "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/mowd-*"
      }
    ]
  })
  
  tags = {
    Name        = "mowd-dynamodb-endpoint-${var.environment}"
    Environment = var.environment
  }
}

# KMS VPC Endpoint
resource "aws_vpc_endpoint" "kms" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.kms"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
  
  tags = {
    Name        = "mowd-kms-endpoint-${var.environment}"
    Environment = var.environment
  }
}

# Secrets Manager VPC Endpoint
resource "aws_vpc_endpoint" "secrets_manager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
  
  tags = {
    Name        = "mowd-secrets-endpoint-${var.environment}"
    Environment = var.environment
  }
}

# Security Groups

# Lambda Security Group
resource "aws_security_group" "lambda" {
  name        = "mowd-lambda-sg-${var.environment}"
  description = "Security group for Lambda functions"
  vpc_id      = aws_vpc.main.id
  
  # Egress to VPC endpoints only
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "HTTPS to VPC endpoints"
  }
  
  # Egress to NAT for external APIs (OpenAI)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS to external APIs"
  }
  
  # Deny all ingress
  
  tags = {
    Name        = "mowd-lambda-sg-${var.environment}"
    Environment = var.environment
  }
}

# VPC Endpoints Security Group
resource "aws_security_group" "vpc_endpoints" {
  name        = "mowd-vpc-endpoints-sg-${var.environment}"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "HTTPS from Lambda functions"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }
  
  tags = {
    Name        = "mowd-vpc-endpoints-sg-${var.environment}"
    Environment = var.environment
  }
}

# Coturn Security Group (for WebRTC)
resource "aws_security_group" "coturn" {
  name        = "mowd-coturn-sg-${var.environment}"
  description = "Security group for Coturn TURN server"
  vpc_id      = aws_vpc.main.id
  
  # DTLS-SRTP on port 443
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DTLS-SRTP over TCP"
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DTLS-SRTP over UDP"
  }
  
  # TURN on port 5349
  ingress {
    from_port   = 5349
    to_port     = 5349
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "TURN over TLS"
  }
  
  ingress {
    from_port   = 5349
    to_port     = 5349
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "TURN over DTLS"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }
  
  tags = {
    Name        = "mowd-coturn-sg-${var.environment}"
    Environment = var.environment
  }
}

# Network ACLs (Defense in Depth)
resource "aws_network_acl" "private" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private[*].id
  
  # Ingress rules
  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = var.vpc_cidr
    from_port  = 443
    to_port    = 443
  }
  
  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }
  
  # Egress rules
  egress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }
  
  egress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = var.vpc_cidr
    from_port  = 1024
    to_port    = 65535
  }
  
  tags = {
    Name        = "mowd-private-nacl-${var.environment}"
    Environment = var.environment
  }
}

# VPC Flow Logs
resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id
  
  tags = {
    Name        = "mowd-flow-logs-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/aws/vpc/mowd-${var.environment}"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.logs.arn
  
  tags = {
    Name        = "mowd-flow-logs-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_iam_role" "flow_logs" {
  name = "mowd-flow-logs-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  name = "flow-logs-policy"
  role = aws_iam_role.flow_logs.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })
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

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

# Outputs
output "vpc_id" {
  value = aws_vpc.main.id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "security_group_ids" {
  value = {
    lambda        = aws_security_group.lambda.id
    vpc_endpoints = aws_security_group.vpc_endpoints.id
    coturn        = aws_security_group.coturn.id
  }
}