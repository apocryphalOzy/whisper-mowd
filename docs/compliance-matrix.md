# HIPAA & GDPR Compliance Matrix

## Feature-to-Control Mapping

| Feature | HIPAA Requirement | GDPR Article | Technical Control | Status |
|---------|------------------|--------------|-------------------|---------|
| User Authentication | 164.312(a)(1) Access Control | Art. 32 Security | Cognito MFA + JWT | ⚪ Planned |
| Audio Encryption | 164.312(a)(2)(iv) Encryption | Art. 32(1)(a) | S3 SSE-KMS | ⚪ Planned |
| Audit Logging | 164.312(b) Audit Controls | Art. 30 Records | CloudTrail Lake | ⚪ Planned |
| Access Monitoring | 164.308(a)(1)(ii)(D) | Art. 32(1)(d) | GuardDuty + SIEM | ⚪ Planned |
| Data Integrity | 164.312(c)(1) | Art. 5(1)(f) | S3 Versioning | ⚪ Planned |
| Transmission Security | 164.312(e)(1) | Art. 32(1)(a) | TLS 1.3 Only | ⚪ Planned |
| User Access Reviews | 164.308(a)(4) | Art. 32(1)(d) | Quarterly IAM Audit | ⚪ Planned |
| Incident Response | 164.308(a)(6) | Art. 33-34 | Automated Runbooks | ⚪ Planned |
| Data Retention | 164.316(b)(2) | Art. 5(1)(e) | S3 Lifecycle Rules | ⚪ Planned |
| Right to Delete | N/A | Art. 17 | GDPR Delete Lambda | ⚪ Planned |
| Data Portability | N/A | Art. 20 | Export API | ⚪ Planned |
| Consent Management | 164.308(a)(3) | Art. 6-7 | Consent Database | ⚪ Planned |
| Breach Detection | 164.308(a)(6)(ii) | Art. 33 | Real-time Alerts | ⚪ Planned |
| Employee Training | 164.308(a)(5) | Art. 39 | Annual Security Training | ⚪ Planned |
| Backup & Recovery | 164.308(a)(7) | Art. 32(1)(c) | Cross-Region Backup | ⚪ Planned |

## HIPAA Technical Safeguards Implementation

### §164.312(a) - Access Control

#### (a)(1) Unique User Identification
- **Implementation**: Cognito User Pools with UUID
- **Configuration**:
  ```
  Username: Email-based
  User ID: Cognito sub (UUID v4)
  Attributes: school_id, role, department
  ```

#### (a)(2)(i) Automatic Logoff
- **Implementation**: JWT expiry + session timeout
- **Configuration**:
  ```
  Access Token: 15 minutes
  Refresh Token: 30 days (with rotation)
  Idle Timeout: 30 minutes
  ```

#### (a)(2)(iii) Encryption and Decryption
- **Implementation**: KMS customer managed keys
- **Configuration**:
  ```
  Audio Files: aws/kms/audio-key
  Transcripts: aws/kms/transcript-key
  Summaries: aws/kms/summary-key
  ```

### §164.312(b) - Audit Controls
- **CloudTrail Configuration**:
  ```
  All API calls logged
  Data events for S3 & DynamoDB
  Insights enabled for anomalies
  90-day retention in CloudTrail Lake
  ```

### §164.312(c) - Integrity Controls
- **S3 Configuration**:
  ```
  Versioning: Enabled
  MFA Delete: Required
  Object Lock: 7-day governance
  Checksums: SHA256 validation
  ```

### §164.312(d) - Person Authentication
- **MFA Requirements**:
  ```
  Setup: Required within 24 hours
  Methods: TOTP, SMS, WebAuthn
  Recovery: Backup codes (encrypted)
  Admin: Hardware keys required
  ```

### §164.312(e) - Transmission Security
- **TLS Configuration**:
  ```
  Minimum Version: TLS 1.3
  Cipher Suites: TLS_AES_256_GCM_SHA384
  HSTS: max-age=31536000
  Certificate: ACM with auto-renewal
  ```

## GDPR Implementation Details

### Article 25 - Data Protection by Design
1. **Privacy-First Architecture**:
   - No persistent storage of IP addresses
   - Automatic PII detection and masking
   - Minimal data collection principle

2. **Default Settings**:
   - Shortest retention periods
   - Opt-in for all features
   - Anonymous usage analytics

### Article 32 - Security of Processing
1. **Pseudonymization**:
   - User IDs separate from PII
   - Hashed identifiers in logs
   - Tokenization of sensitive fields

2. **Confidentiality**:
   - End-to-end encryption
   - Zero-knowledge architecture
   - Client-side encryption option

3. **Resilience**:
   - Multi-AZ deployment
   - Auto-scaling groups
   - Circuit breakers

4. **Testing**:
   - Quarterly penetration tests
   - Chaos engineering
   - Disaster recovery drills

### Article 33 - Breach Notification
**Automated Detection**:
```yaml
Triggers:
  - Mass data access (>1000 records)
  - Unauthorized KMS key usage
  - IAM policy changes
  - Failed decrypt operations
  
Response:
  - Immediate: Block access, snapshot state
  - 1 hour: Security team notification
  - 24 hours: Initial assessment
  - 72 hours: Regulatory notification
```

### Article 35 - Data Protection Impact Assessment
**High-Risk Processing**:
- Voice biometric data
- Minor's educational records
- Large-scale systematic monitoring

**Mitigations**:
- Regular DPIA reviews
- Privacy-enhancing technologies
- Stakeholder consultation

## Compliance Validation

### Technical Controls Testing
```bash
# HIPAA Access Control Test
aws cognito-idp admin-get-user --user-pool-id $POOL --username test@school.edu

# GDPR Encryption Validation  
aws kms describe-key --key-id alias/audio-key --query 'KeyMetadata.KeyUsage'

# Audit Trail Verification
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole

# Data Retention Check
aws s3api get-bucket-lifecycle-configuration --bucket mowd-audio-prod
```

### Compliance Checklist

#### Pre-Production
- [ ] Security assessment complete
- [ ] DPIA documented
- [ ] Encryption verified
- [ ] Access controls tested
- [ ] Audit logs validated
- [ ] Incident response tested

#### Quarterly Reviews
- [ ] Access rights audit
- [ ] Encryption key rotation
- [ ] Backup restoration test
- [ ] Security patches applied
- [ ] Compliance training completed
- [ ] Third-party audits

## Control Exceptions

### Acceptable Risks
1. **CloudWatch Logs**: 30-day retention for cost (mitigated by CloudTrail)
2. **Lambda Cold Starts**: 5-second delay acceptable for batch processing
3. **DynamoDB Eventual Consistency**: Acceptable for metadata queries

### Compensating Controls
1. **No HSM**: KMS provides equivalent key protection
2. **No On-Premise**: Cloud-only with strong access controls
3. **Shared Responsibility**: AWS handles physical security

## Compliance Contacts

- **Data Protection Officer**: dpo@mowd-whisper.com
- **Security Team**: security@mowd-whisper.com
- **HIPAA Privacy Officer**: hipaa@mowd-whisper.com
- **Breach Notification**: incident@mowd-whisper.com (24/7)