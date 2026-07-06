# ruff: noqa: PLR2004
from datetime import datetime

import pytest
from pydantic import ValidationError

from techtrendwatcher.models.github import (
    GithubAPIFull,
    GithubAPIItem,
    GithubSilverRecord,
)

"""
GithubAPIItemの異常系テスト
"""


def test_github_api_item_fail():

    invalid_data = {"id": 1, "name": "Grapgh RAG"}

    with pytest.raises(ValidationError) as exinfo:
        GithubAPIItem(**invalid_data)
    exinfo.value.errors()
    assert "html_url" in str(exinfo.value)


"""
GithubAPIItemの正常系テスト
"""


def test_github_api_item_success():

    valid_data = {
        "id": 1,
        "name": "n8n",
        "html_url": "https://github.com",
        "stargazers_count": 5,
        "description": "有効なテストデータ",
        "language": "Ja",
        "topics": ["ml", "ai"],
    }

    item = GithubAPIItem(**valid_data)
    assert item.id == 1
    assert item.name == "n8n"
    assert item.topics == ["ml", "ai"]


"""
GitHubAPIFullのrow_dataカラムのテスト
"""


def test_github_api_full_raw_data():
    data = {
        "total_count": 1,
        "incomplete_results": False,
        "items": [],
        "extra_field": "row_dataの中身",
    }

    full_model = GithubAPIFull(**data)

    assert full_model.total_count == 1
    assert not full_model.incomplete_results
    assert full_model.row_data["extra_field"] == "row_dataの中身"


"""
GithubSilverRecordの正常系テスト
"""


def test_github_silver_record_datetime():
    data = {
        "id": 1,
        "name": "n8n",
        "stargazers_count": 2,
        "search_query": "Graph",
        "captured_at": "2026-03-30T10:00:00",
        "raw_data": {"key": "value"},
    }

    silver_record = GithubSilverRecord(**data)

    assert isinstance(silver_record.captured_at, datetime)
    assert silver_record.captured_at.year == 2026
