from techtrendwatcher.core.base import BaseTrendSource
from techtrendwatcher.models.base import TrendItem
from pydantic import BaseModel
from typing import Any
import asyncio

class RedditItem(BaseModel):
    """Reddit専用の内部モデルよ。太郎なんていないわ！"""
    id: str
    title: str
    ups: int
    url: str
    selftext: str | None = None

class RedditClient(BaseTrendSource):
    """
    Redditのモッククライアント。
    将来本物を実装する時も、この構造を守れば main.py は直さなくていいのよ。
    """
    async def fetch_trends(self, query: str) -> list[TrendItem]:
        self.logger.info("reddit_fetch_start", query=query)
        
        # APIを叩いたふりをして、dictを返すわ
        mock_raw_data = [
            {
                "id": f"t3_{query}_1",
                "title": f"The ultimate guide to {query} in 2026",
                "ups": 1500,
                "url": f"https://www.reddit.com/r/tech/comments/{query}_guide",
                "selftext": "This is a comprehensive review of the latest trends..."
            }
        ]
        
        normalized_items = []
        for raw in mock_raw_data:
            # 1. 固有モデルでバリデーション
            resp = RedditItem.model_validate(raw)
            
            # 2. 共通モデル(TrendItem)に変換（正規化）
            normalized_items.append(TrendItem(
                source="reddit",
                external_id=resp.id,
                name=resp.title,
                url=resp.url,
                score=resp.ups,
                description=resp.selftext,
                raw_data=resp.model_dump()
            ))
            
        return normalized_items
