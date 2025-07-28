# Changelog

## [Unreleased] - 2025-01-28

### Added
- **Security Features**
  - JWT authentication with AWS Cognito integration
  - Role-based access control (RBAC) 
  - GDPR compliance with deletion handler
  - Structured JSON logging for CloudWatch
  - KMS encryption for all data types
  - Security audit trails

- **Infrastructure**
  - Terraform modules for AWS deployment
  - VPC configuration for network isolation
  - CloudTrail integration
  - GitHub Actions security scanning

- **Documentation**
  - README.md with comprehensive project overview
  - QUICKSTART.md for easy setup
  - Security assessment report
  - Compliance matrix documentation
  - Incident response playbook

- **Development Tools**
  - Setup scripts for Windows (batch and PowerShell)
  - Test scripts for validation
  - Environment configuration templates

### Changed
- Migrated from `aws_storage.py` to `secure_aws_storage.py` with enhanced security
- Updated CLI to use secure storage implementation
- Enhanced requirements.txt with security dependencies
- Improved error handling and logging throughout

### Security
- Implemented HIPAA technical safeguards (45 CFR 164.312)
- Added GDPR Article 17 (Right to Erasure) compliance
- Enabled end-to-end encryption with AWS KMS
- Added comprehensive audit logging
- Implemented secure JWT validation

### Fixed
- Windows compatibility issues with virtual environment
- Path handling for cross-platform support
- Import errors in CLI module

## Previous Versions

### [0.1.0] - Initial Release
- Basic transcription using OpenAI Whisper
- Local file storage
- Simple CLI interface
- OpenAI-based summarization