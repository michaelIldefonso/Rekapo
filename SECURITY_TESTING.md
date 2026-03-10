# Security Testing & Scanning

This document outlines security testing procedures for the Rekapo project.

## Quick Start

```bash
# Backend security scan
cd Rekapo/
python security_scan.py

# Frontend security scan (Admin Panel)
cd Rekapo_admin/
npm audit
npm audit fix  # Auto-fix non-breaking issues

# Frontend security scan (Mobile App - if using npm)
cd RekapoApp/
npm audit
```

---

## Backend Security Tools

### 1. Bandit - Python Security Linter

**Purpose**: Detects common security issues in Python code.

**Checks for**:
- SQL injection vulnerabilities
- Hardcoded passwords/secrets
- Use of insecure functions (eval, exec, pickle)
- Weak cryptographic practices
- Command injection risks

**Installation**:
```bash
pip install bandit
```

**Manual usage**:
```bash
# Full scan with report
bandit -r . -f json -o bandit_report.json

# Screen output with severity levels
bandit -r . -ll  # Show only medium/high severity
```

**Interpreting results**:
- **High severity**: Fix immediately before deployment
- **Medium severity**: Review and fix if applicable
- **Low severity**: Document as accepted risk if not applicable

---

### 2. Safety - Dependency Vulnerability Scanner

**Purpose**: Checks Python dependencies against known CVE database.

**Installation**:
```bash
pip install safety
```

**Usage**:
```bash
# Scan requirements.txt
safety check

# JSON report
safety check --json --output safety_report.json

# Scan specific file
safety check -r requirements-dev.txt
```

**Updating vulnerable packages**:
```bash
# Check outdated packages
pip list --outdated

# Update specific package
pip install --upgrade <package-name>

# Regenerate requirements
pip freeze > requirements.txt
```

---

### 3. Automated Security Scan

Run `security_scan.py` to execute all checks:

```bash
python security_scan.py
```

**Output files**:
- `bandit_report.json` - Security issues in code
- `safety_report.json` - Vulnerable dependencies

---

## Frontend Security Tools

### NPM Audit

**Purpose**: Checks npm dependencies for known vulnerabilities.

**Usage**:
```bash
cd Rekapo_admin/  # or ProgresstifyFrontEnd/
npm audit

# See detailed report
npm audit --json > audit_report.json

# Auto-fix (be careful - may introduce breaking changes)
npm audit fix

# Fix only non-breaking issues
npm audit fix --only=prod
```

---

## Mobile App Security

### Expo Security Considerations

**Best practices**:
1. **Keep Expo SDK updated**: `expo upgrade`
2. **Audit dependencies**: `npm audit` (for any added packages)
3. **Check permissions**: Review `app.json` → `android.permissions`
4. **Secure storage**: Use `expo-secure-store` for sensitive data (already implemented)

**Manual checks**:
```bash
cd RekapoApp/
expo doctor  # Check for common issues
npm audit    # Check dependencies
```

---

## OWASP Mobile Top 10 Checklist

For thesis defense, demonstrate awareness of OWASP Mobile Security:

### ✅ Implemented
- **M1: Improper Platform Usage**: Proper permissions (RECORD_AUDIO) with runtime checks
- **M2: Insecure Data Storage**: Use of expo-secure-store for tokens
- **M5: Insufficient Cryptography**: JWT tokens with signature verification
- **M9: Reverse Engineering**: Hermes bytecode (obfuscation)

### ⚠️ To Improve
- **M3: Insecure Communication**: Add TLS certificate pinning
- **M4: Insecure Authentication**: Add MFA/2FA for admin accounts
- **M6: Insecure Authorization**: Add rate limiting to API endpoints
- **M8: Code Tampering**: Add code integrity checks (ProGuard/R8)

### 🔍 Not Applicable
- **M7: Client Code Quality**: Using TypeScript + ESLint
- **M10: Extraneous Functionality**: No debug code in production builds

---

## Penetration Testing (Optional - Thesis Bonus)

### OWASP ZAP - Web API Testing

**Purpose**: Automated security testing for FastAPI backend.

**Installation**:
```bash
# Download from: https://www.zaproxy.org/download/
```

**Basic usage**:
1. Start Rekapo backend: `python main.py`
2. Run ZAP automated scan against `http://localhost:8000`
3. Export report as PDF for thesis appendix

**Recommended scan**: Spider + Active Scan against `/docs` (Swagger UI)

---

### Mobile App Security Testing (Advanced)

**Tools**:
- **MobSF (Mobile Security Framework)**: Automated APK analysis
- **Burp Suite**: Intercept API traffic between app and backend
- **Frida**: Runtime instrumentation for Android app

**For thesis**: Running basic MobSF scan on APK demonstrates security awareness.

---

## Pre-Deployment Security Checklist

Before deploying to production (for thesis defense talking points):

### Backend
- [ ] Run `python security_scan.py` with 0 critical issues
- [ ] Run `safety check` - all dependencies up-to-date
- [ ] Review `bandit_report.json` - document accepted risks
- [ ] Enable HTTPS-only in production (Nginx/Caddy)
- [ ] Set `JWT_EXPIRE_MINUTES` appropriately (currently 4 hours)
- [ ] Disable `/docs` and `/redoc` in production

### Frontend
- [ ] Run `npm audit` in all frontend projects
- [ ] Update vulnerable packages
- [ ] Enable CSP headers
- [ ] Minify/obfuscate JavaScript

### Mobile
- [ ] Run `expo doctor` - no warnings
- [ ] Review `app.json` permissions - only RECORD_AUDIO
- [ ] Enable ProGuard for Android release builds
- [ ] Remove console.log statements

### Infrastructure
- [ ] Use strong database passwords
- [ ] Enable database SSL connections
- [ ] Restrict Modal API keys to production domains
- [ ] Set up CORS whitelist (remove `allow_origins=["*"]`)
- [ ] Enable rate limiting (FastAPI-Limiter)

---

## Thesis Defense Talking Points

1. **Security Testing Approach**:
   - "Implemented automated security scanning with bandit and safety"
   - "Regular dependency audits via npm audit for frontend"
   - "OWASP Mobile Top 10 compliance review conducted"

2. **Known Limitations** (be honest):
   - "Prototype stage - formal penetration testing planned for production"
   - "No encryption at rest due to time constraints - documented as future work"
   - "Budget constraints required external AI processing - local mode available"

3. **Risk Mitigation**:
   - "JWT tokens expire after 4 hours to limit exposure"
   - "Google OAuth provides baseline authentication security"
   - "Cloudflare R2 for secure object storage"
   - "Signed URLs can be implemented for private file access"

4. **Production Roadmap**:
   - "Security audit with professional pen-testing service"
   - "Implement MFA for admin accounts"
   - "Add encryption at rest for audio files"
   - "Deploy with TLS 1.3 and certificate pinning"

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Mobile Top 10](https://owasp.org/www-project-mobile-top-10/)
- [Python Security Best Practices](https://snyk.io/blog/python-security-best-practices/)
- [Expo Security Guide](https://docs.expo.dev/guides/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
