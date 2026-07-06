# ruff: noqa: PLR2004
from datetime import datetime

import polars as pl

from techtrendwatcher.github.processor import (
    convert_to_silver_dataframe,
    get_trend_dataframe,
)
from techtrendwatcher.models.github import GithubAPIFull, GithubAPIItem


def test_convert_to_silver_dataframe():

    items = [
        GithubAPIItem(
            id=1,
            name="n8n",
            html_url="https://github.com",
            stargazers_count=5,
            description="有効なテストデータ",
            language="Ja",
            topics=["ml", "ai"],
        )
    ]

    resp = GithubAPIFull(total_count=1, incomplete_results=False, items=items)
    query = "GraphRAG"

    df = convert_to_silver_dataframe(resp, query)

    # 列の型は正しいか
    assert isinstance(df, pl.DataFrame)
    assert len(df) == 1

    # 列定義は正しいか
    expected_col = [
        "id",
        "name",
        "stargazers_count",
        "search_query",
        "raw_data",
        "captured_at",
    ]
    assert all(col in df.columns for col in expected_col)

    # 中身は正しいか
    assert df["id"][0] == 1
    assert isinstance(df["raw_data"][0], dict)
    assert df["raw_data"][0]["name"] == "n8n"


"""
比較対象の過去ファイルが存在するケース
"""


def test_get_trend_df_success(mocker, tmp_path):
    # ファイル出力先パスを書き換える
    mock_path = mocker.patch("techtrendwatcher.github.processor.Path")
    mock_path.return_value.parent.parent = tmp_path

    # ディレクトリ準備
    file_dir = tmp_path / "data" / "raw" / "test_query"
    file_dir.mkdir(parents=True)

    # 偽の現在データを作成
    mock_current_df = pl.DataFrame(
        [
            {
                "id": 2,
                "name": "name",
                "stargazers_count": 10,
                "search_query": "RAG",
                "raw_data": {"key": "val"},
                "captured_at": datetime.now(),
            }
        ]
    )

    mock_prev_df_1 = pl.DataFrame(
        [
            {
                "id": 2,
                "name": "name",
                "stargazers_count": 3,
                "search_query": "RAG",
                "raw_data": {"key": "val"},
                "captured_at": datetime.now(),
            }
        ]
    )

    mock_prev_df_2 = pl.DataFrame(
        [
            {
                "id": 2,
                "name": "name",
                "stargazers_count": 5,
                "search_query": "RAG",
                "raw_data": {"key": "val"},
                "captured_at": datetime.now(),
            }
        ]
    )

    mock_prev_df_1.write_parquet(file_dir / "20260301.parquet")
    mock_prev_df_2.write_parquet(file_dir / "20260302.parquet")

    result = get_trend_dataframe(mock_current_df, "test_query")

    assert "star_delta" in result.columns
    assert result["star_delta"][0] == 7


"""
比較対象の過去ファイルが存在しないケース
"""


def test_get_trend_df_fail(mocker, tmp_path):
    # ファイル出力先パスを書き換える
    mock_path = mocker.patch("techtrendwatcher.github.processor.Path")
    mock_path.return_value.parent.parent = tmp_path

    # 偽の現在データを作成
    mock_current_df = pl.DataFrame(
        [
            {
                "id": 1,
                "name": "name",
                "stargazers_count": 10,
                "search_query": "RAG",
                "raw_data": {"key": "val"},
                "captured_at": datetime.now(),
            }
        ]
    )

    result = get_trend_dataframe(mock_current_df, "test_query")

    assert "star_delta" in result.columns
    assert result["star_delta"][0] == 10
