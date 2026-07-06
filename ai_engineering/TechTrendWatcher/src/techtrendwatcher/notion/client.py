from datetime import datetime
from http import HTTPStatus
from typing import Any, NoReturn

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionRateLimitError,
    NotionResourceNotFoundError,
    NotionValidationError,
)
from techtrendwatcher.core.logger import get_logger

# リトライ設定の定数化
NOTION_RETRY_MULTIPLIER = 1
NOTION_RETRY_MIN_WAIT = 2
NOTION_RETRY_MAX_WAIT = 10
NOTION_RETRY_MAX_ATTEMPTS = 3


def retry_log(retry_state):
    logger = get_logger(__name__)
    logger.warning(
        "Notion API接続でリトライ",
        retry_cnt = retry_state.attempt_number,
        retry_reason = retry_state.outcome.exception()
    )


def is_retryable_error(e: Exception):
    if isinstance(e, httpx.RequestError):
        return True
    if isinstance(e, NotionRateLimitError):
        return True
    if isinstance(e, NotionAPIError):
        if getattr(e, "original_error", None) and isinstance(
            e.original_error, httpx.RequestError
        ):
            return True
        if e.status_code in [500, 502, 503, 504]:
            return True
    return False


notion_retry = retry(
    wait=wait_exponential(
        multiplier=NOTION_RETRY_MULTIPLIER,
        min=NOTION_RETRY_MIN_WAIT,
        max=NOTION_RETRY_MAX_WAIT,
    ),
    stop=stop_after_attempt(NOTION_RETRY_MAX_ATTEMPTS),
    retry=retry_if_exception(is_retryable_error),
    before_sleep=retry_log,
    reraise=True,
)


class NotionClient:
    def __init__(self, client: httpx.AsyncClient):
        self.logger = get_logger(__name__)
        settings = get_settings()
        self.client = client
        self.notion_token = settings.notion_token
        self.database_id = settings.notion_database_id

        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    async def _handle_http_error(self, e: httpx.HTTPStatusError) -> NoReturn:
        status_code = e.response.status_code
        if status_code == HTTPStatus.UNAUTHORIZED:
            raise NotionAuthError(
                "Notionトークンが無効です。確認してください",
                status_code=status_code,
                original_error=e,
            ) from e

        if status_code == HTTPStatus.FORBIDDEN:
            raise NotionAuthError(
                "オブジェクトにアクセスする権限がありません",
                status_code=status_code,
                original_error=e,
            )

        if status_code == HTTPStatus.NOT_FOUND:
            raise NotionResourceNotFoundError(
                "DBが見つからない。IDを確認せよ",
                status_code=status_code,
                original_error=e,
            ) from e
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise NotionRateLimitError(
                "Notionのレート制限です", status_code=status_code, original_error=e
            ) from e
        if status_code == HTTPStatus.BAD_REQUEST:
            raise NotionValidationError(
                "リクエストが不正です", status_code=status_code, original_error=e
            ) from e
        raise NotionAPIError(
            f"Notion APIでエラーが発生した：{e}",
            status_code=status_code,
            original_error=e,
        ) from e

    """
    githubの差分に対して、
    notionを検索し、repoの情報がすでに記載されていれば、update
    reoiの情報がなければinsertを行う
    """

    async def upsert_repo(self, row: dict[str, Any]) -> None:
        page_id = await self.query_page_by_github_id(githubid=row["id"])
        if page_id:
            await self.update_notion_record(
                page_id=page_id, stars=row["stargazers_count"], delta=row["star_delta"]
            )
        else:
            await self.create_page(
                githubid=row["id"],
                name=row["name"],
                stars=row["stargazers_count"],
                delta=row["star_delta"],
                url=row["html_url"],
            )

    """
    すでに対象のリポジトリがデータベースに存在するかを判定する
    """

    @notion_retry
    async def query_page_by_github_id(self, githubid: int) -> str | None:
        endpoint = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        payload = {"filter": {"property": "GithubID", "number": {"equals": githubid}}}

        try:
            response = await self.client.post(
                endpoint, headers=self.headers, json=payload
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if len(results) > 0:
                page_id = results[0]["id"]
                if isinstance(page_id, str):
                    self.logger.info("success_notion_query", page_id = page_id)
                    return page_id
                else:
                    raise ValueError(f"Unexpexted page_id type: {type(page_id)}")
            else:
                self.logger.info("notionのクエリ結果が0件")
                return None

        except httpx.HTTPStatusError as e:
            await self._handle_http_error(e)
        except Exception as e:
            if not isinstance(e, NotionAPIError):
                raise NotionAPIError(
                    f"想定外の理由でNotionへの検索が失敗:{e}", original_error=e
                ) from e
            raise

    """
    初回の書き込み
    初回書き込みのretryはnotionで成功⇨respのnw切断。
    プログラム側は失敗と認識、再実行。がありうるので本来的には結果確認をして、retryにすべきではある。
    """

    @notion_retry
    async def create_page(
        self, githubid: int, name: str, stars: int, delta: int, url: str
    ) -> dict[str, Any] | None:

        self.logger.info("create_pageの処理開始")
        current_time = datetime.now().isoformat()

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "GithubID": {"number": githubid},
                "Name": {"title": [{"text": {"content": name}}]},
                "Stars": {"number": stars},
                "Delta": {"number": delta},
                "URL": {"url": url},
                "UpdatedTime": {"date": {"start": current_time}},
            },
        }

        try:
            response = await self.client.post(
                "https://api.notion.com/v1/pages", headers=self.headers, json=payload
            )
            response.raise_for_status()
            self.logger.info(f"notionへの書き込み成功{response}")
            data = response.json()
            if not isinstance(data, dict):
                raise NotionAPIError(
                    f"Notionからのレスポンス形式が不正です（期待: dict, 実際: {type(data)}）",
                    status_code=response.status_code,
                )

            return data

        except httpx.HTTPStatusError as e:
            await self._handle_http_error(e)
        except Exception as e:
            if not isinstance(e, NotionAPIError):
                raise NotionAPIError(
                    f"想定外の理由でNotionの書き込みが失敗:{e}", original_error=e
                ) from e
            raise

    """
    すでに対象のレコード（GithubID）がNotion上にあるなら
    updateを行う
    """

    @notion_retry
    async def update_notion_record(
        self, stars: int, delta: int, page_id: str
    ) -> dict[str, Any] | None:

        endpoint = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {
            "properties": {
                "Stars": {"number": stars},
                "Delta": {"number": delta},
                "UpdatedTime": {"date": {"start": datetime.now().isoformat()}},
            }
        }

        try:
            response = await self.client.patch(
                endpoint, headers=self.headers, json=payload
            )
            response.raise_for_status()
            if response.status_code != HTTPStatus.OK:
                self.logger.info(f"Notion Update Error Detail: {response.text}")
            data = response.json()
            if not isinstance(data, dict):
                raise NotionAPIError(
                    f"Notionのページ更新のレスポンスが不正です。data:{data}",
                    status_code=response.status_code,
                )
            return data
        except httpx.HTTPStatusError as e:
            await self._handle_http_error(e)
        except Exception as e:
            if not isinstance(e, NotionAPIError):
                raise NotionAPIError(
                    f"想定外の理由でNotionの更新が失敗:{e}", original_error=e
                ) from e
            raise
