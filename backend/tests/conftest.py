"""Test-only configuration supplied before application modules are imported."""

import os


os.environ.update(
    {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "JIRA_BASE_URL": "https://jira.example.test",
        "JIRA_EMAIL": "technical-user@example.test",
        "JIRA_API_TOKEN": "test-token",
        "JIRA_MAX_RETRIES": "2",
        "JIRA_RETRY_BASE_SECONDS": "0.01",
        "JIRA_PROJECT_KEYS": "IN",
        "SYNC_DEFAULT_CRON": "0 * * * *",
    }
)
