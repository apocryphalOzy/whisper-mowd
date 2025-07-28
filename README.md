# MOWD Whisper - Secure Transcription & Summarization Platform

A HIPAA and GDPR-compliant cloud-based platform for educational audio transcription and AI-powered summarization.

## Overview

MOWD Whisper leverages OpenAI's Whisper model for accurate speech-to-text transcription and LLMs for intelligent summarization, specifically designed for educational institutions. The platform emphasizes security, compliance, and scalability.

## Features

- **Audio Transcription**: High-accuracy transcription using OpenAI Whisper
- **AI Summarization**: Intelligent bullet-point summaries using GPT/Claude
- **Multi-format Support**: MP3, WAV, M4A, MP4, and more
- **Security-First Architecture**: End-to-end encryption with AWS KMS
- **HIPAA/GDPR Compliant**: Full compliance with healthcare and privacy regulations
- **Scalable Infrastructure**: AWS-based architecture with auto-scaling
- **Real-time Processing**: Asynchronous processing with progress tracking

## Architecture

```
User → CloudFront → API Gateway → Lambda Functions → S3/DynamoDB
                                          ↓
                                   Whisper/LLM Processing
```

### Key Components

- **Authentication**: AWS Cognito with MFA
- **Storage**: S3 with KMS encryption, lifecycle policies
- **Processing**: Lambda functions in private VPC
- **Database**: DynamoDB for metadata
- **Monitoring**: CloudWatch, GuardDuty, CloudTrail

## Quick Start

### Prerequisites

- Python 3.9+
- AWS Account with appropriate permissions
- OpenAI API key (for GPT summarization)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/whisper-mowd.git
   cd whisper-mowd
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r whisper-mowd/requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp whisper-mowd/env-example.txt whisper-mowd/.env
   # Edit .env with your configuration
   ```

5. **Run locally**
   ```bash
   python whisper-mowd/src/cli.py --audio sample.mp3 --output output/
   ```

## Deployment

### AWS Infrastructure Setup

1. **Initialize Terraform**
   ```bash
   cd terraform/environments/prod
   terraform init
   ```

2. **Plan deployment**
   ```bash
   terraform plan -var-file="prod.tfvars"
   ```

3. **Apply infrastructure**
   ```bash
   terraform apply -var-file="prod.tfvars"
   ```

### CI/CD Pipeline

The project includes GitHub Actions workflows for:
- Security scanning (CodeQL, Snyk, tfsec)
- Automated testing
- Deployment to AWS

## Usage

### Command Line Interface

```bash
# Basic transcription
python whisper-mowd/src/cli.py --audio lecture.mp3

# With summarization
python whisper-mowd/src/cli.py --audio lecture.mp3 --summarizer openai

# Batch processing
python whisper-mowd/scripts/process_batch.py --directory audio_files/ --recursive
```

### API Endpoints

- `POST /transcribe` - Upload and transcribe audio
- `GET /transcript/{id}` - Retrieve transcript
- `GET /summary/{id}` - Retrieve summary
- `POST /gdpr/delete` - GDPR deletion request

## Security

### Encryption
- **At Rest**: S3 SSE-KMS, DynamoDB encryption
- **In Transit**: TLS 1.3 minimum
- **Key Management**: AWS KMS with 90-day rotation

### Compliance
- HIPAA Technical Safeguards (164.312)
- GDPR Articles 17, 25, 32-34
- SOC 2 Type II ready

### Data Retention
- Audio files: 30 days (automatic deletion)
- Transcripts: 18 months
- Audit logs: 90 days

## Development

### Project Structure
```
whisper-mowd/
├── src/              # Source code
│   ├── cli.py        # CLI interface
│   ├── auth/         # Authentication
│   ├── storage/      # Storage implementations
│   ├── transcription/# Whisper integration
│   └── summarization/# LLM integration
├── tests/            # Unit tests
├── scripts/          # Utility scripts
└── terraform/        # Infrastructure as Code
```

### Testing
```bash
# Run unit tests
pytest whisper-mowd/tests/

# Run security scan
python -m bandit -r whisper-mowd/src/

# Check code quality
python -m pylint whisper-mowd/src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/your-org/whisper-mowd/issues)
- Security: security@mowd-whisper.com

## License

Copyright © 2024 MOWD Whisper. All rights reserved.

---

For detailed documentation, see the [docs/](docs/) directory.