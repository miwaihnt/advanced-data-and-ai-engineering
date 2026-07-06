from http import HTTPStatus

import httpx
import pytest
import respx

from techtrendwatcher.core.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
)
from techtrendwatcher.github.client import (
    GITHUB_RETRY_MAX_ATTEMPTS,
    GithubClient,
)


# 成功
@pytest.mark.asyncio
async def test_search_github_success():
    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "total_count": 1,
                        "incomplete_results": False,
                        "items": [
                            {
                                "id": 1,
                                "name": "test-repo",
                                "html_url": "https://github.com/test",
                                "stargazers_count": 100,
                                "description": "test description",
                                "topics": [],
                            }
                        ],
                    },
                )
            )

            result = await github_client.search_github("RAG")

            assert result.total_count == 1
            assert result.items[0].id == 1


# 認証のエラー
@pytest.mark.asyncio
async def test_search_github_fail_auth():
    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(HTTPStatus.UNAUTHORIZED)
            )

            with pytest.raises(GitHubAuthError) as exinfo:
                await github_client.search_github("RAG")

            assert "認証エラー" in str(exinfo.value)


# Ratelimitエラー
@pytest.mark.asyncio
async def test_search_github_fail_ratelimit(mocker):
    mocker.patch("asyncio.sleep", return_value=None)

    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            route = respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(HTTPStatus.FORBIDDEN)
            )

            with pytest.raises(GitHubRateLimitError) as exinfo:
                await github_client.search_github("RAG")

            assert "レート制限" in str(exinfo.value)
            assert route.call_count == GITHUB_RETRY_MAX_ATTEMPTS


# サーバエラー
@pytest.mark.asyncio
async def test_search_github_fail_server_err(mocker):
    mocker.patch("asyncio.sleep", return_value=None)

    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            route = respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(HTTPStatus.INTERNAL_SERVER_ERROR)
            )

            with pytest.raises(GitHubAPIError) as exinfo:
                await github_client.search_github("RAG")

            assert "GitHub APIでエラーが発生したわよ" in str(exinfo.value)
            assert route.call_count == GITHUB_RETRY_MAX_ATTEMPTS


# リクエストエラー (接続失敗)
@pytest.mark.asyncio
async def test_search_github_fail_request_err(mocker):
    mocker.patch("asyncio.sleep", return_value=None)

    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            route = respx.get("https://api.github.com/search/repositories").mock(
                side_effect=httpx.RequestError("Connection failed")
            )

            with pytest.raises(GitHubAPIError) as exinfo:
                await github_client.search_github("RAG")

            assert "Githubへの接続が失敗" in str(exinfo.value)
            assert route.call_count == GITHUB_RETRY_MAX_ATTEMPTS
