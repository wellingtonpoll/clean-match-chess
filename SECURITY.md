# Security Policy

Clean Match Chess is a forensic-analytics platform. Integrity of its
outputs — and confidentiality of any submitted PGN — are first-class
concerns. This document is the canonical policy for reporting and
handling security issues.

## Supported versions

| Version    | Status              | Security fixes      |
| ---------- | ------------------- | ------------------- |
| `1.0.x`    | ✅ Active           | Yes                 |
| `< 1.0.0`  | ❌ Pre-release      | No (please upgrade) |

We support only the latest minor release with security fixes. New
minors land at most quarterly; the latest is always the safest.

## Reporting a vulnerability

**Please do NOT open a public issue for a security report.**

Use GitHub's private vulnerability reporting flow:

1. Go to https://github.com/wellingtonpoll/clean-match-chess/security
2. Click **Report a vulnerability**.
3. Fill the form. Include: affected version, reproduction steps, a
   minimal PGN or input that triggers the issue, expected vs observed
   behaviour, and any suggested mitigation.

If for any reason the GitHub flow is unavailable, send an encrypted
email to **wellingtonpoleti@gmail.com** with the subject prefix
`[CMC-SECURITY]`. We will follow up with a private GitHub advisory.

## Service-level commitments

| Severity     | Initial acknowledgement | Patch target               |
| ------------ | ----------------------- | -------------------------- |
| Critical     | 24 hours                | 7 calendar days            |
| High         | 48 hours                | 30 calendar days           |
| Medium / Low | 5 business days         | Next minor or patch release|

"Critical" includes any defect that:

- Permits remote code execution from a crafted PGN or chess.com response.
- Enables manifest forgery (an audit-replay attack: same `run_id`
  reaching a different score).
- Discloses an input PGN or its derived report bundle to an
  unauthorised third party.

"High" includes determinism breaks, broken signature/hash invariants
on the reproducibility manifest, or any defect that lets a
non-canonical risk treatment slip past the four locked audits.

## What we will do

- Confirm receipt within the SLA above.
- Triage privately. We will share the assigned severity within five
  business days.
- Develop a fix on a private branch; back-port to supported versions.
- Publish a GitHub Security Advisory and request a CVE if external
  consumers may be affected.
- Credit you in the advisory and `CHANGELOG.md`, unless you request
  otherwise.

## What we ask

- Give us reasonable time to ship a fix before public disclosure.
- Avoid testing against accounts, PGNs, or data you do not own.
- Do not exfiltrate data beyond what is necessary to prove the issue.
- Do not perform denial-of-service or social-engineering tests
  against the project or its maintainers.

## Out of scope

- Findings that require physical access to a contributor's machine.
- Defects in dependencies that we have not vendored. Please report
  those upstream and we will mirror the advisory if needed.
- Theoretical attacks without a working proof-of-concept.

## No bug bounty

Clean Match Chess is an open-source project without commercial
funding. We deeply appreciate disclosures and credit every reporter
in the advisory, but we are not able to offer monetary rewards at
this time.
