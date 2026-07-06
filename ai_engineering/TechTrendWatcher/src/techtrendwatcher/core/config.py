from functools import lru_cache

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from techtrendwatcher.core.exceptions import ConfigurationError


class SnowflakeConfig(BaseModel):
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema_name: str = Field(alias="schema")
    table: str


class Settings(BaseSettings):
    """
    .envの読み込みと設定
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="_", extra="ignore"
    )

    """githubの設定"""
    search_query: list[str] = ["Graph RAG"]
    github_token: str

    """notionの設定"""
    notion_token: str
    notion_database_id: str
    notion_semaphore: int

    """snowflakeの設定"""
    snowflake: SnowflakeConfig


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        raise ConfigurationError(
            message="環境設定時にエラーが発生しました。処理を中断します",
            original_error=e,
        ) from e

    except Exception as e:
        raise ConfigurationError(
            message="環境設定時に予期せぬエラーが発生しました。処理を中断します",
            original_error=e,
        ) from e
