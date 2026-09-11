# Agent Instructions

Pointers and operational constraints for AI coding agents working in this repository.

## Documentation Index

| Purpose | Document |
|---|---|
| Navigation router, universal invariants, dev commands, env vars | [`CLAUDE.md`](CLAUDE.md) |
| Backend directory tree, request lifecycle, layering, and database schema | [`docs/claude/architecture.md`](docs/claude/architecture.md) |
| Global coding conventions, response contracts, error handling, retries | [`docs/claude/conventions.md`](docs/claude/conventions.md) |
| Feature specifications, routes, services, UI components, and gotchas | [`docs/claude/features.md`](docs/claude/features.md) |
| Jira Cloud HTTP client signatures, auth modes, pagination, and retry logic | [`docs/claude/api-clients.md`](docs/claude/api-clients.md) |
| Background sync worker, APScheduler lifecycle, watermark state machine | [`docs/claude/async-tasks.md`](docs/claude/async-tasks.md) |
| Frontend directory structure, design tokens, component library, tests | [`docs/claude/frontend.md`](docs/claude/frontend.md) |
| Production Docker Compose deployment, reverse proxy setup, upgrade steps | [`docs/deployment.md`](docs/deployment.md) |
| Documentation organization, file ownership, and update triggers | [`docs/documentation-rules.md`](docs/documentation-rules.md) |

## Operational Warnings

- **Jira rate limits**: Jira Cloud enforces strict outbound rate limits (HTTP 429 with `Retry-After`). The sync worker uses exponential backoff. Never script rapid iterative sync loops or direct API queries against Jira.
- **Single-flight sync runs**: Never trigger concurrent sync runs. The `sync_state` cursor table is a single-row singleton; concurrent executions race on the watermark and duplicate Jira requests.
- **No authentication in application**: This application relies entirely on network-level isolation. Never expose service ports directly to public networks, and never configure `CORS_ALLOWED_ORIGINS` to `*`.
- **Adhere to invariants**: Every code change must maintain the numbered invariants enumerated in [`CLAUDE.md`](CLAUDE.md).
