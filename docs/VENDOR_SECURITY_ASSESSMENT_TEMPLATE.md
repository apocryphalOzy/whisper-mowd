# Vendor Security Assessment Template
## For Third-Party Service Evaluation

### Vendor Information
- **Vendor Name**: ___________________
- **Service/Product**: ___________________
- **Assessment Date**: ___________________
- **Assessor**: ___________________
- **Risk Rating**: ☐ Low ☐ Medium ☐ High ☐ Critical

---

## 1. Data Security & Privacy

### Data Handling
| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| What types of data will the vendor process? | | | |
| Where is data stored geographically? | | | |
| Is data encrypted at rest? (Algorithm/Key Management) | | | |
| Is data encrypted in transit? (TLS version) | | | |
| How is data segregated between customers? | | | |
| What is the data retention policy? | | | |
| How is data destroyed at end of life? | | | |

### Privacy & Compliance
| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| Is vendor GDPR compliant? | | | |
| Is vendor HIPAA compliant? | | | |
| Will vendor sign a BAA? | | | |
| Are subprocessors used? | | | |
| How are data subject requests handled? | | | |
| Is privacy policy publicly available? | | | |

---

## 2. Access Control & Authentication

| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| How is user authentication implemented? | | | |
| Is MFA supported/required? | | | |
| How are privileged accounts managed? | | | |
| What is the password policy? | | | |
| How is access logging implemented? | | | |
| Are there role-based access controls? | | | |
| How often are access reviews conducted? | | | |

---

## 3. Security Controls & Monitoring

### Technical Controls
| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| What security monitoring is in place? | | | |
| Is there 24/7 security operations? | | | |
| How are security patches managed? | | | |
| What DDoS protection exists? | | | |
| Is there a Web Application Firewall? | | | |
| How is malware protection implemented? | | | |

### Incident Response
| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| Is there an incident response plan? | | | |
| What is the breach notification timeline? | | | |
| Who is the security contact? | | | |
| How are customers notified of incidents? | | | |
| Is cyber insurance maintained? | | | |

---

## 4. Infrastructure & Architecture

| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| What cloud providers are used? | | | |
| Is infrastructure multi-tenant or dedicated? | | | |
| How is high availability achieved? | | | |
| What is the backup strategy? | | | |
| What is the disaster recovery RTO/RPO? | | | |
| Are there geographic redundancies? | | | |

---

## 5. Development & Change Management

| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| Is secure SDLC followed? | | | |
| How is code security tested? | | | |
| Are security scans automated? | | | |
| How are changes deployed? | | | |
| Is there a rollback procedure? | | | |
| How are dependencies managed? | | | |

---

## 6. Third-Party Audits & Certifications

| Certification/Audit | Available | Date | Notes |
|-------------------|-----------|------|-------|
| SOC 2 Type II | ☐ Yes ☐ No | | |
| ISO 27001 | ☐ Yes ☐ No | | |
| PCI DSS | ☐ Yes ☐ No | | |
| HITRUST | ☐ Yes ☐ No | | |
| Penetration Test Report | ☐ Yes ☐ No | | |
| Vulnerability Scan Results | ☐ Yes ☐ No | | |

---

## 7. Business Continuity

| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| What is the financial stability? | | | |
| Is there key person dependency? | | | |
| What is the SLA commitment? | | | |
| Is there 24/7 support? | | | |
| What is the contract termination process? | | | |
| How is data exported/migrated? | | | |

---

## 8. Specific to WebRTC/Real-Time Services

| Question | Response | Risk Level | Notes |
|----------|----------|------------|-------|
| How are STUN/TURN servers secured? | | | |
| Is DTLS-SRTP enforced? | | | |
| How is signaling authenticated? | | | |
| Are media streams recorded? | | | |
| How is quality of service monitored? | | | |
| What geographic regions are supported? | | | |

---

## Risk Assessment Summary

### Identified Risks
1. **High Risk**: 
2. **Medium Risk**: 
3. **Low Risk**: 

### Recommended Mitigations
1. 
2. 
3. 

### Overall Recommendation
☐ **Approve** - Acceptable risk level
☐ **Approve with Conditions** - Requires specific controls
☐ **Further Review** - Need additional information
☐ **Reject** - Unacceptable risk level

### Conditions for Approval (if applicable)
1. 
2. 
3. 

### Review Schedule
- **Initial Review**: ___________________
- **Annual Review**: ___________________
- **Trigger Events**: M&A, breach, compliance change

---

## Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Security Officer | | | |
| Legal/Compliance | | | |
| Business Owner | | | |
| IT Management | | | |

---

## Appendix: Required Documents

### From Vendor
- [ ] Security policies and procedures
- [ ] Most recent audit reports (SOC 2, etc.)
- [ ] Penetration test executive summary
- [ ] Insurance coverage details
- [ ] Incident response plan summary
- [ ] Architecture diagrams
- [ ] Data flow diagrams

### Internal Documents
- [ ] Data classification for shared data
- [ ] Business impact analysis
- [ ] Legal review of contracts
- [ ] Integration security requirements