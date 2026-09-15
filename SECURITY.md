# Security Policy

## Supported versions

Only the latest version on the default branch is supported.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's
private security advisory reporting for this repository and include a minimal
reproduction, affected component, and impact. Maintainers will acknowledge the
report and coordinate a fix privately before disclosure.

## Deployment boundary

This application has no application-level authentication. It must be deployed
behind authenticated VPN/SSO and a TLS reverse proxy; never expose its Compose
ports directly to the Internet.
