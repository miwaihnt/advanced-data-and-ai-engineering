from http import HTTPStatus
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.base import BaseTrendSource 
from techtrendwatcher.core.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
    GitHubValidationError,
)
from techtrendwatcher.core.logger import get_logger
from techtrendwatcher.models.github import GithubAPIFull, TrendItem

# リトライ設定の定数化
GITHUB_RETRY_MULTIPLIER = 1
GITHUB_RETRY_MIN_WAIT = 4
GITHUB_RETRY_MAX_WAIT = 60
GITHUB_RETRY_MAX_ATTEMPTS = 5


# retry条件を決める
def is_retryable_error(exception: Exception) -> bool:
    # timeout
    if isinstance(exception, httpx.RequestError):
        return True
    # レート制限
    if isinstance(exception, GitHubRateLimitError):
        return True

    if isinstance(exception, GitHubAPIError):
        if getattr(exception, "original_error", None) and isinstance(
            exception.original_error, httpx.RequestError
        ):
            return True
        if exception.status_code in [500, 502, 503, 504]:
            return True

    return False


def retry_log(retry_state):
    logger = get_logger(__name__)
    logger.warning(
        "GitHub APIのリトライ中。。。",
        retry_cnt = retry_state.attempt_number,
        retry_reason = retry_state.outcome.exception()
    )


class GithubClient(BaseTrendSource):
    # __init__ は親クラスのものを継承するから、特殊なことがなければ書かなくていいわ！

    # 検索
    @retry(
        wait=wait_exponential(
            multiplier=GITHUB_RETRY_MULTIPLIER,
            min=GITHUB_RETRY_MIN_WAIT,
            max=GITHUB_RETRY_MAX_WAIT,
        ),
        stop=stop_after_attempt(GITHUB_RETRY_MAX_ATTEMPTS),
        retry=retry_if_exception(is_retryable_error),
        before_sleep=retry_log,
        reraise=True,
    )
    async def fetch_trends(self, query: str) -> list[TrendItem]:
        url = "https://api.github.com/search/repositories"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.setting.github_token}",
            "X-Github-Api-Version": "2022-11-28",
        }

        params: dict[str, Any] = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 5,
        }

        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            response_json = response.json()
            full_result = GithubAPIFull.model_validate(response_json)

            # 共通モデルへのマッピング（データの正規化）
            return [
                TrendItem(
                    source="github",
                    external_id=str(item.id),
                    name=item.name,
                    url=item.html_url,
                    score=item.stargazers_count,
                    description=item.description,
                    raw_data=item.model_dump()
                )
                for item in full_result.items
            ]

        except httpx.HTTPStatusError as e:
            # Httpエラー
            status_code = e.response.status_code

            if status_code == HTTPStatus.UNAUTHORIZED:
                raise GitHubAuthError(
                    "Github認証エラーが発生しました。認証トークンを確認してください",
                    status_code=status_code,
                    original_error=e,
                ) from e

            if status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS):
                raise GitHubRateLimitError(
                    "レート制限よ！少し頭を冷やしなさい！",
                    status_code=status_code,
                    original_error=e,
                ) from e

            if status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                raise GitHubValidationError(
                    "クエリがデタラメよ！", status_code=status_code, original_error=e
                ) from e

            raise GitHubAPIError(
                f"GitHub APIでエラーが発生したわよ: {e}",
                status_code=status_code,
                original_error=e,
            ) from e

        except httpx.RequestError as e:
            # タイムアウトを捕まえる
            raise GitHubAPIError(f"Githubへの接続が失敗:{e}", original_error=e) from e

        except Exception as e:
            raise GitHubAPIError("予期せぬエラーが発生したわ", original_error=e) from e
