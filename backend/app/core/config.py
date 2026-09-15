from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_max_retries: int = Field(ge=0, le=10)
    jira_retry_base_seconds: float = Field(ge=0, le=60)
    jira_timeout_seconds: float = Field(gt=0, le=300)
    # Raw comma-separated string from JIRA_PROJECT_KEYS; use `jira_project_keys`
    # below to get it as a parsed list.
    jira_project_keys_raw: str = Field(validation_alias="JIRA_PROJECT_KEYS")

    sync_default_cron: str

    # Comma-separated list of origins allowed to call this API via CORS.
    # There is no authentication in this app by design (internal network
    # only) -- a wildcard origin would let any reachable webpage read
    # timesheet data or trigger a sync, so this must be the frontend's
    # actual origin(s), not "*".
    cors_allowed_origins_raw: str = Field(
        default="http://localhost:3000", validation_alias="CORS_ALLOWED_ORIGINS"
    )

    @field_validator("jira_base_url")
    @classmethod
    def validate_jira_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("JIRA_BASE_URL must be an absolute HTTPS URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("JIRA_BASE_URL must not contain credentials")
        return value

    @field_validator("cors_allowed_origins_raw")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one explicit origin")
        if "*" in origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain a wildcard")

        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(f"Invalid CORS origin: {origin!r}")
        return ",".join(origins)

    @property
    def jira_project_keys(self) -> list[str]:
        return [key.strip() for key in self.jira_project_keys_raw.split(",") if key.strip()]

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins_raw.split(",") if origin.strip()]


settings = Settings()
