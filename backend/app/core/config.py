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
    jira_worklog_jql: str = ""

    sync_default_cron: str

    @property
    def jira_project_keys(self) -> list[str]:
        return [key.strip() for key in self.jira_project_keys_raw.split(",") if key.strip()]


settings = Settings()
