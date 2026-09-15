"""Security-sensitive application configuration validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    values = {
        "database_url": "sqlite+pysqlite:///:memory:",
        "jira_base_url": "https://jira.example.test",
        "jira_email": "technical-user@example.test",
        "jira_api_token": "test-token",
        "jira_max_retries": 2,
        "jira_retry_base_seconds": 0.01,
        "jira_timeout_seconds": 5,
        "JIRA_PROJECT_KEYS": "IN",
        "sync_default_cron": "0 * * * *",
        "CORS_ALLOWED_ORIGINS": "http://localhost:3000",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("value", ["*", "", "https://valid.test/path", "ftp://valid.test"])
def test_cors_origins_reject_unsafe_values(value: str) -> None:
    with pytest.raises(ValidationError):
        _settings(CORS_ALLOWED_ORIGINS=value)


def test_cors_origins_are_normalized() -> None:
    settings = _settings(CORS_ALLOWED_ORIGINS=" https://one.test/,http://localhost:3000 ")

    assert settings.cors_allowed_origins == ["https://one.test", "http://localhost:3000"]


@pytest.mark.parametrize(
    "value",
    ["http://jira.example.test", "jira.example.test", "https://user:secret@jira.example.test"],
)
def test_jira_base_url_requires_https_without_embedded_credentials(value: str) -> None:
    with pytest.raises(ValidationError):
        _settings(jira_base_url=value)
