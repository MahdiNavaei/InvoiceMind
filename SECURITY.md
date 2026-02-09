# Security Policy

This document describes how to report security vulnerabilities for **InvoiceMind** and what to expect from the response process.

## Supported Versions

| Version | Supported |
| --- | --- |
| `main` (latest commit) | Yes |
| Latest tagged release (`v0.x`) | Yes |
| Older releases | No |

## Reporting a Vulnerability

Please report vulnerabilities privately.

1. Preferred: GitHub private advisory  
   `https://github.com/MahdiNavaei/InvoiceMind/security/advisories/new`
2. Fallback: Contact maintainer privately via GitHub profile  
   `https://github.com/MahdiNavaei`

Do **not** open a public issue for an unpatched vulnerability.

## What to Include in the Report

- Affected component(s) and endpoint(s)
- Reproduction steps (minimal PoC)
- Impact assessment (confidentiality/integrity/availability)
- Suggested mitigation (if available)
- Environment details (OS, Python/Node version, config context)

## Response Targets (Best Effort)

- Initial acknowledgment: within **72 hours**
- Triage and severity classification: within **7 days**
- Patch timeline target:
  - Critical: 1-3 days
  - High: 3-7 days
  - Medium: 7-21 days
  - Low: next planned release

## Disclosure Policy

- We follow coordinated disclosure.
- A vulnerability is disclosed publicly **after** a fix or mitigation is available.
- Credit is given to reporters unless they request anonymity.

## Security Scope (In Scope)

- Authentication and authorization (`/v1/auth`, role guards)
- Run lifecycle controls (`create/cancel/replay/export`)
- Quarantine and reprocess flows
- Audit trail integrity (hash-chain tamper resistance)
- Input validation and upload constraints
- Secret/config handling and dependency risk

## Out of Scope

- Vulnerabilities requiring physical host access
- Social engineering/phishing attacks
- Findings in unsupported historical versions

## Operational Security Notes

- Default local credentials in docs are for development only and must never be used in production.
- Change `INVOICEMIND_JWT_SECRET` before any non-local deployment.
- Never commit `.env` files, tokens, or production secrets.
- Use least-privilege roles and rotate credentials regularly.

## Safe Harbor

Security research performed in good faith, without data exfiltration/destruction and without service disruption, is considered authorized.
