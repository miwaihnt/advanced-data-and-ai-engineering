from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""GithubAPIのItems内の各要素"""


class GithubAPIItem(BaseModel):
    id: int
    name: str
    html_url: str
    stargazers_count: int
    description: str
    language: str | None = None
    topics: list[str]


"""Notionに蓄積する必要なものだけを集めたclass"""


class GithubAPISummary(BaseModel):
    total_count: int
    items: list[GithubAPIItem] = []


"""Githubから取得する全量を保持"""


class GithubAPIFull(BaseModel):
    model_config = ConfigDict(extra="allow")
    total_count: int
    incomplete_results: bool
    items: list[GithubAPIItem] = Field(default_factory=list)
    raw_data: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def capture_raw_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["row_data"] = data
        return data


"""SnowflakeといったWHのRaw層に蓄積するclass"""


class GithubSilverRecord(BaseModel):
    id: int
    name: str
    stargazers_count: int
    search_query: str
    captured_at: datetime
    raw_data: dict[str, Any]


"""Github以外のAPIソースに対応するための共通モデル"""
class TrendItem(BaseModel):
    source: str
    external_id: int
    name: str
    url: str
    score: int
    description: str
    raw_data: dict[str, Any]

"""Reddit APIからのレスポンスモデル"""
class Reddit(BaseModel):
    id: int
    title: str
    score: int
    url: str
    description: str
