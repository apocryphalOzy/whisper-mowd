# Demo Guide for Interview - Whisper MOWD Security Features

## Quick Start Demo

### Option 1: Simple CLI Demo (Recommended for Interview)

```bash
# 1. Navigate to project
cd whisper-mowd

# 2. Activate environment (if needed)
# Windows:
..\Scripts\activate
# Mac/Linux:
source ../bin/activate

# 3. Run a quick transcription with security features
python src/cli.py --audio data/audio/20250429_112153_saqt.mp3 --output output/ --summarizer openai

# 4. Show the security logging
python src/logging/structured_logger.py
```

### Option 2: Web Demo (If Internet Available)

```bash
# 1. Navigate to demo directory
cd demo

# 2. Run the demo app
python app_demo.py

# 3. Open browser to http://localhost:8000
# 4. Use password: whisper2025
```

## Key Security Features to Demonstrate

### 1. Authentication & Access Control
**What to show:**
- JWT validation code in `src/auth/jwt_validator.py`
- Role-based access decorators
- MFA configuration in comments

**Talking points:**
- "Here's our JWT validation middleware that verifies Cognito tokens"
- "Notice the role-based access control - teachers can delete, students can only view"
- "MFA is enforced at the Cognito level with 24-hour setup requirement"

### 2. Encryption Implementation
**What to show:**
- KMS configuration in `terraform/modules/security/crypto.tf`
- Encryption at rest in S3 configuration
- Key rotation policies

**Talking points:**
- "We use separate KMS keys for audio, transcripts, and summaries"
- "Automated 90-day key rotation is configured here"
- "All data is encrypted at rest with customer-managed keys"

### 3. GDPR Compliance
**What to show:**
- GDPR deletion handler: `src/gdpr/deletion_handler.py`
- Audit trail creation
- Complete data removal across all systems

**Talking points:**
- "This implements Article 17 - Right to Erasure"
- "Notice how we track all deletions for compliance"
- "The function removes data from S3, DynamoDB, and all backups"

### 4. Incident Response
**Files to reference:**
- `docs/incident-response-playbook.md`
- Automated response examples

**Talking points:**
- "15-minute P1 response time with automated containment"
- "Here's how we automatically disable compromised accounts"
- "CloudWatch triggers Lambda functions for immediate response"

### 5. Compliance Matrix
**What to show:**
- `docs/compliance-matrix.md`
- Specific HIPAA controls implementation
- Testing commands at the bottom

**Talking points:**
- "Every HIPAA requirement maps to a specific technical control"
- "We can verify compliance with these automated checks"
- "Status tracking ensures nothing falls through the cracks"

## Demo Script (5 minutes)

### Opening (30 seconds)
"I'd like to show you the security implementation for Whisper MOWD, a HIPAA and GDPR-compliant audio transcription platform I built. This demonstrates my approach to security-first development."

### Architecture Overview (1 minute)
*Show `docs/SECURITY_PRESENTATION.md` slide 3*
"The architecture implements defense in depth with multiple security layers:
- CloudFront for DDoS protection
- WAF for application security
- Cognito with MFA for authentication
- Encrypted storage with KMS
- All in private VPC with monitoring"

### Live Code Demo (2 minutes)
*Show JWT validator code*
"Here's the authentication middleware that validates tokens and enforces role-based access. Notice the comprehensive claim validation and automatic session timeout."

*Show GDPR deletion handler*
"This implements GDPR Article 17 compliance. It finds all user data across our systems and removes it completely while maintaining an audit trail."

*Show Terraform security module*
"Infrastructure as code ensures consistent security deployment. These KMS keys rotate automatically and have strict access policies."

### Compliance & Monitoring (1 minute)
*Show compliance matrix*
"Every compliance requirement maps to technical controls. We track implementation status and have automated verification."

*Reference incident response playbook*
"The incident response plan includes automated containment - for example, if unauthorized KMS access is detected, the system automatically disables the user and alerts the security team."

### Closing (30 seconds)
"This project showcases my approach to building security into applications from the ground up, with particular focus on healthcare compliance and automated security operations. I'm excited to bring this experience to WebRTC applications."

## Backup Materials

If demo fails, have these ready:
1. Screenshots of the running application
2. PDF of the security architecture
3. Code snippets of key security features
4. Compliance matrix printed out

## Common Questions During Demo

**Q: "How long did this take to build?"**
A: "The core security architecture was designed and implemented over 3 months, with ongoing enhancements for compliance and automation."

**Q: "What was the biggest security challenge?"**
A: "Balancing HIPAA's strict access controls with GDPR's data portability requirements. We solved it with granular permissions and comprehensive audit logging."

**Q: "How would this apply to WebRTC?"**
A: "The same principles apply - authentication for signaling, encryption for media streams, audit logging for connections, and automated threat response. The main addition would be TURN server security and real-time monitoring."

**Q: "What would you do differently?"**
A: "I'd implement more proactive security testing earlier, add chaos engineering for incident response validation, and integrate security scanning into the CI/CD pipeline from day one."

## Final Tips

1. **Keep it focused**: Security architecture, not application features
2. **Be specific**: Point to actual code and configurations
3. **Show automation**: Emphasize automated security operations
4. **Connect to role**: Relate everything back to their needs
5. **Stay calm**: If something breaks, explain what it would show

Good luck with the interview!