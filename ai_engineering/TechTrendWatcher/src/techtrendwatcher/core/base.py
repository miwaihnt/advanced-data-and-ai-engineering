import httpx
from abc import ABC, abstractmethod
from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.logger import get_logger
from techtrendwatcher.models.base import TrendItem

class BaseTrendSource(ABC):
    """
    全てのデータソースクライアントの基底クラス。
    共通の設定保持とロギング、インターフェースの強制を行うわ。
    """
    def __init__(self, client: httpx.AsyncClient):
        self.setting = get_settings()
        self.client = client
        # クラス名に基づいたロガーを自動生成。これで子クラスでいちいち作らなくて済むわ！
        self.logger = get_logger(self.__class__.__module__)

    @abstractmethod
    async def fetch_trends(self, query: str) -> list[TrendItem]:
        """このメソッドを実装しない子クラスは認めないわよ！"""
        pass
