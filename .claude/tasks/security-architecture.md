# Security Architecture & Threat Model

## System Overview
MOWD Whisper is a cloud-based transcription platform processing sensitive educational audio content through OpenAI Whisper and LLM summarization.

## Data Flow Map

```
[User Device] --HTTPS/TLS1.3--> [CloudFront]
                                      |
                                      v
                              [API Gateway + WAF]
                                      |
                                 [Cognito JWT]
                                      |
                                      v
                               [Lambda Functions]
                                    /    \
                                   /      \
                                  v        v
                          [S3-KMS Audio] [DynamoDB]
                                  |
                                  v
                           [Whisper Lambda]
                                  |
                                  v
                          [S3-KMS Transcripts]
                                  |
                                  v
                            [LLM Lambda]
                                  |
                                  v
                          [S3-KMS Summaries]
```

## Threat Actors

### External Threats
- **Nation-state actors**: Target educational data for intelligence
- **Cybercriminals**: Ransom sensitive recordings or sell data
- **Hacktivists**: Disrupt educational services or leak content
- **Script kiddies**: Opportunistic attacks on exposed endpoints

### Internal Threats
- **Malicious insiders**: Employees with privileged access
- **Compromised accounts**: Legitimate users with stolen credentials
- **Third-party risks**: AWS account compromise, supply chain attacks

## Trust Boundaries

### Boundary 1: Internet → AWS Edge
- **Controls**: CloudFront DDoS protection, TLS 1.3, Origin Access Identity
- **Threats**: DDoS, MitM, DNS hijacking

### Boundary 2: Edge → Application
- **Controls**: WAF rules, API throttling, JWT validation
- **Threats**: Injection attacks, broken authentication, excessive API calls

### Boundary 3: Application → Data
- **Controls**: IAM roles, VPC endpoints, KMS encryption
- **Threats**: Privilege escalation, data exfiltration, key compromise

### Boundary 4: Cross-Service
- **Controls**: Service-to-service authentication, least privilege
- **Threats**: Lateral movement, service impersonation

## Data Classification

### Tier 1: Highly Sensitive
- **Raw audio files**: Contains voices, PII, educational content
- **Access**: Encrypted at rest (KMS), time-limited presigned URLs
- **Retention**: 30 days maximum

### Tier 2: Sensitive  
- **Transcripts**: Text representation of audio
- **Access**: Encrypted at rest, school-based access control
- **Retention**: Academic year + 1 year

### Tier 3: Internal
- **Summaries**: AI-generated bullet points
- **Access**: Read-only for authorized users
- **Retention**: Same as transcripts

### Tier 4: Metadata
- **Processing logs**: Timestamps, IDs, status
- **Access**: Administrative only
- **Retention**: 90 days

## Attack Vectors & Mitigations

### 1. Audio Upload Attacks
**Vector**: Malicious audio files (polyglot files, oversized uploads)
**Mitigations**:
- File type validation (magic bytes)
- Size limits (max 500MB)
- Virus scanning with Lambda + ClamAV
- Separate processing VPC

### 2. Injection Attacks
**Vector**: Filename manipulation, metadata injection
**Mitigations**:
- Input sanitization
- Parameterized queries
- Content Security Policy headers
- SQL injection impossible (NoSQL DynamoDB)

### 3. Authentication Bypass
**Vector**: JWT manipulation, session hijacking
**Mitigations**:
- Cognito-issued JWTs only
- 15-minute token expiry
- Refresh token rotation
- MFA enforcement

### 4. Data Exfiltration
**Vector**: Bulk API calls, insider downloads
**Mitigations**:
- API rate limiting (100 req/min)
- CloudWatch anomaly detection
- S3 bucket policies deny public access
- VPC endpoints prevent internet routing

### 5. Privilege Escalation
**Vector**: Lambda role assumption, policy manipulation
**Mitigations**:
- Explicit deny policies
- No wildcard permissions
- STS session tags
- CloudTrail monitoring all AssumeRole

### 6. Supply Chain
**Vector**: Compromised dependencies, malicious packages
**Mitigations**:
- Dependency pinning with hashes
- Snyk vulnerability scanning
- Private PyPI mirror
- Docker base image scanning

### 7. Ransomware
**Vector**: KMS key deletion, S3 object lock bypass
**Mitigations**:
- KMS key deletion protection (7-day minimum)
- S3 Object Lock in governance mode
- Cross-region replication
- Immutable backups

## Cryptographic Architecture

### Data at Rest
- **S3 Objects**: SSE-KMS with customer managed keys
- **DynamoDB**: AWS managed encryption
- **EBS Volumes**: Encrypted by default

### Data in Transit
- **Public Internet**: TLS 1.3 minimum, HSTS enabled
- **Within VPC**: TLS 1.2+ for all internal APIs
- **Media Streams**: DTLS-SRTP for WebRTC

### Key Management
- **KMS Keys**: Separate keys per data type (audio, transcript, summary)
- **Rotation**: Automatic 90-day rotation via aliases
- **Access**: CloudTrail logs all key usage
- **Backup**: Multi-region key replicas

## Security Controls by Layer

### Network Layer
- VPC with private subnets only
- No internet gateway on data processing VPC
- VPC Flow Logs to S3
- Network ACLs deny by default

### Application Layer  
- Lambda functions in private subnets
- No persistent compute instances
- Secrets Manager for API keys
- Environment variables encrypted

### Data Layer
- S3 bucket policies enforce encryption
- DynamoDB point-in-time recovery
- Automated backups with 35-day retention
- Cross-region replication for DR

## Compliance Mappings

### HIPAA Technical Safeguards
- Access Control (164.312(a)): Cognito + IAM
- Audit Controls (164.312(b)): CloudTrail Lake
- Integrity (164.312(c)): S3 versioning + MFA delete
- Transmission Security (164.312(e)): TLS 1.3

### GDPR Requirements
- Encryption (Article 32): End-to-end encryption
- Right to Erasure (Article 17): Automated deletion Lambda
- Data Portability (Article 20): JSON export API
- Breach Notification (Article 33): CloudWatch alarms

## Incident Response Triggers

### Critical (P1)
- KMS key access from unknown IP
- Mass data download (>1000 objects/hour)
- IAM policy changes
- Failed MFA challenges (>5 in 10 min)

### High (P2)
- Unusual API patterns
- Lambda function errors (>10%)
- DynamoDB throttling
- S3 bucket policy changes

### Medium (P3)
- Failed login attempts
- Deprecated TLS usage
- Cost anomalies (>50% increase)