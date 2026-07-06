from pydantic import BaseModel
from typing import Any

class TrendItem(BaseModel):
    """
    プラットフォーム（GitHub/Reddit等）を問わず、
    データパイプライン内で共通して扱うトレンドアイテムの正規化モデル。
    """
    source: str
    external_id: str
    name: str
    url: str
    score: int
    description: str | None = None
    raw_data: dict[str, Any]
