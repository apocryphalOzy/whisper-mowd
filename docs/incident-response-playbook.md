# Incident Response Playbook

## Quick Reference

**Security Hotline**: +1-XXX-XXX-XXXX (24/7)  
**Incident Email**: incident@mowd-whisper.com  
**Status Page**: https://status.mowd-whisper.com

## Incident Classification

| Severity | Response Time | Examples |
|----------|--------------|----------|
| P1 Critical | 15 min | Data breach, ransomware, KMS compromise |
| P2 High | 1 hour | Service outage, DDoS, authentication bypass |
| P3 Medium | 4 hours | Performance degradation, single user compromise |
| P4 Low | 24 hours | Failed phishing, policy violations |

## Response Team

### Core Team
- **Incident Commander (IC)**: Overall coordination
- **Technical Lead**: Technical investigation and remediation
- **Security Lead**: Forensics and threat analysis
- **Communications Lead**: Internal/external communications
- **Legal/Compliance**: HIPAA/GDPR notifications

### Escalation Chain
1. On-call Engineer → Security Team Lead
2. Security Team Lead → CTO
3. CTO → CEO + Legal Counsel
4. CEO → Board of Directors (P1 only)

## Response Phases

### 1. DETECTION (0-15 minutes)

**Automated Alerts**:
```bash
# Check CloudWatch dashboard
aws cloudwatch get-metric-statistics \
  --namespace MOWD/Security \
  --metric-name UnauthorizedKMSAccess \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Manual Checks**:
```bash
# Recent GuardDuty findings
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{"Criterion":{"severity":{"Gte":4},"updatedAt":{"Gte":1}}}'

# CloudTrail suspicious activity
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)
```

### 2. TRIAGE (15-30 minutes)

**Data Collection Checklist**:
- [ ] Screenshot all alerts and dashboards
- [ ] Export CloudTrail logs for affected timeframe
- [ ] Capture VPC Flow Logs
- [ ] List affected resources (users, data, services)
- [ ] Identify attack vector and scope

**Impact Assessment**:
```bash
# Check affected S3 buckets
aws s3api list-buckets --query 'Buckets[?contains(Name, `mowd`)]'

# Recent data access
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S)
```

### 3. CONTAINMENT (30-60 minutes)

**Immediate Actions**:

1. **Isolate Affected Resources**:
```bash
# Disable compromised IAM user
aws iam update-access-key --access-key-id $KEY_ID --status Inactive

# Revoke all sessions
aws sts get-session-token --duration-seconds 1

# Update security group to block access
aws ec2 modify-security-group-rules \
  --group-id $SG_ID \
  --security-group-rules "SecurityGroupRuleId=$RULE_ID,SecurityGroupRule={IpProtocol=-1,CidrIpv4=0.0.0.0/0,Description='BLOCKED-INCIDENT'}"
```

2. **Preserve Evidence**:
```bash
# Snapshot affected resources
aws ec2 create-snapshot --volume-id $VOLUME_ID --description "Incident-$INCIDENT_ID"

# Export logs
aws logs create-export-task \
  --log-group-name /aws/lambda/mowd-transcribe \
  --from $(date -d '24 hours ago' +%s)000 \
  --to $(date +%s)000 \
  --destination mowd-incident-evidence \
  --destination-prefix incident-$INCIDENT_ID
```

3. **Enable Enhanced Monitoring**:
```bash
# Enable S3 access logging
aws s3api put-bucket-logging \
  --bucket mowd-audio-prod \
  --bucket-logging-status file://logging-config.json

# Increase CloudTrail data events
aws cloudtrail put-event-selectors \
  --trail-name mowd-cloudtrail \
  --event-selectors file://enhanced-selectors.json
```

### 4. ERADICATION (1-4 hours)

**Remove Threat**:
1. Reset all potentially compromised credentials
2. Patch identified vulnerabilities
3. Remove malicious code/artifacts
4. Update WAF rules to block attack patterns

```bash
# Rotate KMS keys
aws kms update-alias \
  --alias-name alias/mowd-audio-prod \
  --target-key-id $NEW_KEY_ID

# Force password reset
aws cognito-idp admin-reset-user-password \
  --user-pool-id $POOL_ID \
  --username $USERNAME
```

### 5. RECOVERY (2-8 hours)

**Service Restoration**:
1. Verify clean state of all systems
2. Restore from known-good backups if needed
3. Gradually restore access
4. Monitor for anomalies

```bash
# Restore from backup
aws backup start-restore-job \
  --recovery-point-arn $RECOVERY_POINT \
  --iam-role-arn $BACKUP_ROLE \
  --resource-type DynamoDB

# Re-enable services
aws lambda update-function-configuration \
  --function-name mowd-transcribe \
  --environment Variables={RESTORE_MODE=false}
```

### 6. POST-INCIDENT (24-72 hours)

**Documentation**:
- Timeline of events
- Root cause analysis
- Affected data inventory
- Remediation actions taken
- Lessons learned

**Notifications**:
- Internal stakeholders
- Affected customers (if applicable)
- Regulatory bodies (HIPAA: 60 days, GDPR: 72 hours)
- Cyber insurance carrier

## Specific Playbooks

### A. Data Breach Response

1. **Immediate**: Disable all external access
```bash
aws s3api put-bucket-policy --bucket mowd-audio-prod --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Principal":"*","Action":"*","Resource":"*"}]}'
```

2. **Assess**: Determine what data was accessed
```sql
-- CloudWatch Insights query
fields @timestamp, userIdentity.arn, requestParameters.bucketName, requestParameters.key
| filter eventName = "GetObject"
| stats count() by userIdentity.arn
```

3. **Notify**: Prepare breach notification letters
- What happened
- When it occurred  
- What data was involved
- Steps taken
- Customer actions required

### B. Ransomware Response

1. **Isolate**: Disconnect affected systems
2. **Identify**: Determine ransomware variant
3. **Restore**: Use immutable backups
```bash
# List available recovery points
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name mowd-backup-vault

# Restore to new resources
aws backup start-restore-job \
  --recovery-point-arn $ARN \
  --metadata '{"NewTableName":"mowd-metadata-restored"}'
```

4. **Report**: File FBI IC3 report
5. **Never pay ransom**

### C. Account Takeover

1. **Lock Account**:
```bash
aws cognito-idp admin-disable-user \
  --user-pool-id $POOL_ID \
  --username $USERNAME
```

2. **Audit Activity**:
```bash
# Check recent actions
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=$USERNAME \
  --max-results 50
```

3. **Reset & Notify**:
- Force password reset
- Invalidate all sessions
- Enable MFA
- Notify user

### D. DDoS Attack

1. **Enable AWS Shield Advanced** (if not already)
2. **Scale Resources**:
```bash
# Update API Gateway throttling
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations op=replace,path=/throttle/rateLimit,value=100
```

3. **Block Sources**:
- Update WAF rules
- Geo-blocking if appropriate
- Rate limiting per IP

## Communication Templates

### Internal Alert
```
INCIDENT ALERT - [P1/P2/P3/P4]
Time Detected: [TIME UTC]
Type: [Breach/Outage/Attack]
Impact: [Systems/Data affected]
IC: [Name]
Bridge: [Phone/Slack]
Status Page Updated: [Y/N]
```

### Customer Notification
```
Subject: Important Security Update

Dear [Customer],

We are writing to inform you of a security incident that may have affected your data.

What Happened: [Brief description]
When: [Date range]
What Information Was Involved: [Data types]
What We Are Doing: [Actions taken]
What You Should Do: [Customer actions]

We take the security of your data seriously and apologize for any inconvenience.

Questions? Contact security@mowd-whisper.com
```

### Regulatory Notification (GDPR)
```
Data Breach Notification under Article 33 GDPR

1. Nature of breach: [Description]
2. Categories and approximate number of data subjects: [Details]
3. Categories and approximate number of records: [Details]
4. Name and contact of DPO: [Contact]
5. Likely consequences: [Assessment]
6. Measures taken: [Technical and organizational measures]
```

## Tools & Resources

### Investigation Tools
- **AWS CLI**: Pre-configured with incident response profile
- **CloudTrail Lake**: SQL queries for investigation
- **GuardDuty**: Threat intelligence
- **VPC Flow Logs**: Network analysis
- **X-Ray**: Application tracing

### Key Commands Reference
```bash
# Export evidence
./scripts/export-evidence.sh $INCIDENT_ID

# Block all access
./scripts/emergency-lockdown.sh

# Restore from backup
./scripts/restore-from-backup.sh $BACKUP_ID

# Generate compliance report
./scripts/generate-breach-report.sh $INCIDENT_ID
```

### External Resources
- AWS Security: https://aws.amazon.com/security/
- SANS Incident Handling: https://www.sans.org/incident-response
- NIST Incident Response: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf

## Testing & Drills

### Monthly Tests
- Pager rotation test
- Backup restoration
- Runbook walkthrough

### Quarterly Drills  
- Tabletop exercise (rotating scenarios)
- Technical drill (simulated incident)
- Communication drill

### Annual Requirements
- Third-party incident response retainer
- Penetration testing
- Red team exercise
- Playbook review and update

---

**Remember**: In an incident, speed matters but accuracy matters more. When in doubt, escalate.