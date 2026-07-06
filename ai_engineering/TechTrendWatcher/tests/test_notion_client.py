from http import HTTPStatus

import httpx
import pytest
import respx

from techtrendwatcher.core.exceptions import (
    NotionAuthError,
    NotionRateLimitError,
)
from techtrendwatcher.notion.client import (
    NOTION_RETRY_MAX_ATTEMPTS,
    NotionClient,
)


# 正常系１：検索⇨新規作成
@pytest.mark.asyncio
async def test_notion_client_create_success():
    async with httpx.AsyncClient() as client:
        notion_client = NotionClient(client)

        with respx.mock:
            query_route = respx.post(url__regex=r".*/databases/.*/query").mock(
                return_value=httpx.Response(200, json={"results": []})
            )

            create_route = respx.post("https://api.notion.com/v1/pages").mock(
                return_value=httpx.Response(200, json={"id": "new_page"})
            )

            row = {
                "id": 123,
                "name": "repo-a",
                "stargazers_count": 100,
                "star_delta": 5,
                "html_url": "https://github.com/test",
            }
            await notion_client.upsert_repo(row)

            assert query_route.call_count == 1
            assert create_route.call_count == 1


# 正常系２：検索⇨更新
@pytest.mark.asyncio
async def test_notion_client_update_success():
    async with httpx.AsyncClient() as client:
        notion_client = NotionClient(client)

        with respx.mock:
            query_route = respx.post(url__regex=r".*/databases/.*/query").mock(
                return_value=httpx.Response(
                    200, json={"results": [{"id": "page_123"}]}
                )
            )

            update_route = respx.patch(url__regex=r".*/pages/page_123").mock(
                return_value=httpx.Response(200, json={"id": "page_123"})
            )

            row = {
                "id": 123,
                "name": "repo-a",
                "stargazers_count": 100,
                "star_delta": 5,
                "html_url": "https://github.com/test",
            }
            await notion_client.upsert_repo(row)

            assert query_route.call_count == 1
            assert update_route.call_count == 1


# 異常系1：検索時に失敗：retry
@pytest.mark.asyncio
async def test_notion_client_search_fail(mocker):
    mocker.patch("asyncio.sleep", return_value=None)

    async with httpx.AsyncClient() as client:
        notion_client = NotionClient(client)

        with respx.mock:
            query_route = respx.post(url__regex=r".*/databases/.*/query").mock(
                return_value=httpx.Response(HTTPStatus.TOO_MANY_REQUESTS)
            )

            row = {
                "id": 123,
                "name": "repo-a",
                "stargazers_count": 100,
                "star_delta": 5,
                "html_url": "https://github.com/test",
            }

            with pytest.raises(NotionRateLimitError) as exinfo:
                await notion_client.upsert_repo(row)

            assert "レート制限" in str(exinfo.value)
            assert query_route.call_count == NOTION_RETRY_MAX_ATTEMPTS


# 異常系2:検索時に失敗：retryしない（NotionAuthErrorのパターン）
@pytest.mark.asyncio
async def test_notion_client_auth_fail(mocker):
    mocker.patch("asyncio.sleep", return_value=None)

    async with httpx.AsyncClient() as client:
        notion_client = NotionClient(client)

        with respx.mock:
            query_route = respx.post(url__regex=r".*/databases/.*/query").mock(
                return_value=httpx.Response(HTTPStatus.FORBIDDEN)
            )

            row = {
                "id": 123,
                "name": "repo-a",
                "stargazers_count": 100,
                "star_delta": 5,
                "html_url": "https://github.com/test",
            }

            with pytest.raises(NotionAuthError) as exinfo:
                await notion_client.upsert_repo(row)

            assert "オブジェクトにアクセスする権限がありません" in str(exinfo.value)
            assert query_route.call_count == 1
