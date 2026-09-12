from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_max_retries: int
    jira_retry_base_seconds: float
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

    @property
    def jira_project_keys(self) -> list[str]:
        return [key.strip() for key in self.jira_project_keys_raw.split(",") if key.strip()]

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins_raw.split(",") if origin.strip()]


settings = Settings()
