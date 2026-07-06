import pytest

from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.exceptions import ConfigurationError

"""
正常系のテスト
"""


def test_setting_config_collect(monkeypatch):

    # テスト用の環境変数をセット
    # Github
    monkeypatch.setenv("github_token", "fake_github_token")
    monkeypatch.setenv("notion_token", "fake_notion_token")
    monkeypatch.setenv("notion_database_id", "fake_db_id")
    monkeypatch.setenv("notion_semaphore", "5")

    # Snowflakeの設定（ネストしてるから 'snowflake_' をつけるのよ！）
    monkeypatch.setenv("snowflake_account", "fake_account")
    monkeypatch.setenv("snowflake_user", "fake_user")
    monkeypatch.setenv("snowflake_password", "fake_password")
    monkeypatch.setenv("snowflake_role", "fake_role")
    monkeypatch.setenv("snowflake_warehouse", "fake_warehouse")
    monkeypatch.setenv("snowflake_database", "fake_db")
    monkeypatch.setenv(
        "snowflake_schema", "fake_schema"
    )  # alias="schema" だからこれでOK
    monkeypatch.setenv("snowflake_table", "fake_table")

    # 実行
    settings = get_settings()
    assert settings.github_token == "fake_github_token"


"""
異常系テスト環境設定
"""


def test_setting_config_raise_error(monkeypatch, tmp_path):

    # カレントディレクトリを空ディレクトリに移動
    # .envを見えなくする
    monkeypatch.chdir(tmp_path)

    # 環境変数を空にする
    monkeypatch.delenv("notion_token", raising=False)

    # ConfigurationErrorの発生を期待
    with pytest.raises(ConfigurationError) as exinfo:
        get_settings()
    assert "環境設定時にエラーが発生しました。処理を中断します" in str(exinfo)
