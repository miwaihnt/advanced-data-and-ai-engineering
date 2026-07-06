class TechTrendError(Exception):
    """Base exception class for this project"""

    pass


class ConfigurationError(TechTrendError):
    """設定ファイルに関するエラーを補足する"""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class ExternalAPIError(TechTrendError):
    """外部API（Github,Notion等）との通信エラーの基底クラス"""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.original_error = original_error


# Github用
class GitHubAPIError(ExternalAPIError):
    """Github API特有の基底エラー"""

    pass


class GitHubRateLimitError(GitHubAPIError):
    """レート制限（403/429）による一時的なエラー"""

    pass


class GitHubAuthError(GitHubAPIError):
    """認証失敗のエラー"""

    pass


class GitHubValidationError(GitHubAPIError):
    """クエリのバリデータションエラー"""

    pass


# Notion用
class NotionAPIError(ExternalAPIError):
    """Notion API特有の基底エラー"""

    pass


class NotionAuthError(NotionAPIError):
    """Notionの認証エラー(401)"""

    pass


class NotionRateLimitError(NotionAPIError):
    """Notionのレート制限(429)"""

    pass


class NotionResourceNotFoundError(NotionAPIError):
    """リソース（DB/Page）が見つからないエラー"""

    pass


class NotionValidationError(NotionAPIError):
    """リクエストのバリデータションエラー（400）"""

    pass


# Snowflake
class SnowflakeAPIError(ExternalAPIError):
    """Snowflake API特有の基底エラー"""

    def __init__(
            self, 
            message, 
            status_code = None, 
            error_code: int | None = None,
            reason: str | None = None,
            original_error: Exception | None = None) -> None:
        
        super().__init__(message, status_code, original_error)
        self.error_code = error_code
        self.reason = reason


class SnowflakeAuthError(SnowflakeAPIError):
    """Snowflakeへの接続に関するエラー"""
    pass
