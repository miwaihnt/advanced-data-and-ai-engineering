import asyncio
import logging
import time
import unittest
from collections import deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FastAPIQueueMonitor")

# 🚨 アラート発火のしきい値
ALERT_THRESHOLD = 3


# ==========================================
# 課題10の移動窓集計クラス
# ==========================================
class ErrorMonitor:
    def __init__(self, window_size_seconds: float = 60.0):
        self.window_size = window_size_seconds
        self.timestamps = deque()

    def _purge_old_data(self, current_timestamp: float) -> None:
        limit = current_timestamp - self.window_size
        while self.timestamps and self.timestamps[0] < limit:
            self.timestamps.popleft()

    def record_error(self, timestamp: float) -> int:
        self._purge_old_data(timestamp)
        self.timestamps.append(timestamp)
        return len(self.timestamps)


# ==========================================
# アプリケーション状態のカプセル化クラス
#
# 【設計判断】
# グローバル変数（log_queue / monitor / consumer_task）を3つ宣言する代わりに、
# このクラスの1インスタンスに状態を集約する。
#
# メリット：
#   - global 宣言が不要になり、state.xxx で直接アクセス可能
#   - startup / shutdown のライフサイクル処理がメソッドとしてカプセル化される
#   - 将来のテストでインスタンスを差し替える（DI）ことが容易になる
#
# プロダクションでの一般的な選択肢：
#   - 小規模  → グローバル変数（シンプルだが管理が難しい）
#   - 中規模  → AppState クラス + lifespan（★今回採用）
#   - 大規模  → FastAPI の app.state + 依存性注入フレームワーク
# ==========================================
class AppState:
    def __init__(self):
        self.log_queue: asyncio.Queue = None
        self.monitor: ErrorMonitor = None
        self.consumer_task: asyncio.Task = None

    async def startup(self):
        """アプリ起動時の初期化処理"""
        self.log_queue = asyncio.Queue()
        self.monitor = ErrorMonitor()
        self.consumer_task = asyncio.create_task(
            log_consumer_loop(self.monitor, self.log_queue)
        )
        logger.info("AppState initialized.")

    async def shutdown(self):
        """アプリ終了時のクリーンアップ処理"""
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                # キャンセル完了（CancelledError の伝播）を待ってから終了する
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("AppState cleaned up.")


# ==========================================
# FastAPI アプリと AppState の初期化
#
# 【設計判断】
# 旧方式の @app.on_event("startup") / @app.on_event("shutdown") は
# FastAPI 0.93+ で非推奨（deprecated）となったため、
# 現在の推奨パターンである lifespan コンテキストマネージャを採用する。
#
# lifespan のメリット：
#   - startup と shutdown の処理が yield の前後に隣接して書ける
#   - リソースの「開く ↔ 閉じる」の対応関係が明確になり、閉じ忘れバグを防げる
#   - Python の with 文（コンテキストマネージャ）と同じ設計思想
# ==========================================

# グローバル変数 3つの代わりに AppState インスタンス1つだけ
state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリのライフサイクル管理。yield の上が startup、下が shutdown。"""
    await state.startup()
    yield
    await state.shutdown()


app = FastAPI(lifespan=lifespan)


# リクエスト用 Pydantic モデル
class ErrorEvent(BaseModel):
    timestamp: float


# 模擬アラート送信関数
async def trigger_alert(count: int):
    logger.warning(f"[ALERT] Direct Action Required! Error count reached: {count}")


# ==========================================
# バックグラウンドワーカー（コンシューマ）
#
# 【設計判断】
# asyncio.create_task で起動した常駐タスク。
# await queue.get() で新しいデータが入るまでイベントループに制御を返し続ける。
# ==========================================
async def log_consumer_loop(monitor: ErrorMonitor, queue: asyncio.Queue):
    """
    キューからタイムスタンプを無限に取り出して ErrorMonitor で集計する常駐タスク。
    """
    logger.info("Log consumer loop started.")
    try:
        while True:
            # アイテムが入るまでイベントループに制御を返しながら待機（非ブロッキング）
            timestamp = await queue.get()

            # エラーを記録し、窓内の現在のエラー件数を集計
            count = monitor.record_error(timestamp)

            # しきい値以上に達したらアラートを発火
            if count >= ALERT_THRESHOLD:
                await trigger_alert(count)

            # 処理完了をキューに通知
            queue.task_done()

    except asyncio.CancelledError:
        # shutdown 時に consumer_task.cancel() が呼ばれると、
        # await queue.get() の時点でこの例外が発生する。
        # raise で再 raise して、shutdown 側の await consumer_task に伝播させる。
        logger.info("Log consumer loop was cancelled.")
        raise
    except Exception as e:
        logger.error(f"Error in consumer loop: {e}")



# ==========================================
# FastAPI エンドポイント
# ==========================================
@app.post("/errors", status_code=status.HTTP_202_ACCEPTED)
async def report_error(event: ErrorEvent):
    """
    エラーログを受け取り、キューに非ブロッキングで投入して即座に 202 を返すエンドポイント。

    【非ブロッキング設計のポイント】
    put_nowait() はキューへの投入が一瞬（数マイクロ秒）で完了する。
    集計処理（record_error や trigger_alert）はワーカーに委ねるため、
    このエンドポイントはブロッキングな処理を一切実行しない。
    """
    # global 宣言不要！state 経由で直接アクセス
    state.log_queue.put_nowait(event.timestamp)
    return {"status": "accepted", "timestamp": event.timestamp}


# ==========================================
# 動作検証用の統合テストケース
# ==========================================
class TestFastAPIQueueMonitor(unittest.TestCase):
    def setUp(self):
        # TestClient をコンテキストマネージャとして手動制御することで、
        # テストごとに startup → test → shutdown のライフサイクルを再現する
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def test_non_blocking_error_reporting(self):
        """
        APIが即座に 202 Accepted を返し、
        非同期でバックグラウンド集計が行われることをテストする。
        """
        response1 = self.client.post("/errors", json={"timestamp": 10.0})
        self.assertEqual(response1.status_code, 202)
        self.assertEqual(response1.json()["status"], "accepted")

        response2 = self.client.post("/errors", json={"timestamp": 20.0})
        self.assertEqual(response2.status_code, 202)

        # バックグラウンドワーカーが処理を完了するまで少し待つ
        time.sleep(0.1)

        # global 宣言不要！state.monitor で直接アクセス
        self.assertEqual(len(state.monitor.timestamps), 2)

    def test_alert_triggering(self):
        """
        3件のエラーが窓内に記録された時にしきい値に達することと、
        古いデータが正しくパージされることをテストする。
        """
        self.client.post("/errors", json={"timestamp": 100.0})
        self.client.post("/errors", json={"timestamp": 110.0})
        self.client.post("/errors", json={"timestamp": 120.0})

        time.sleep(0.1)
        self.assertEqual(len(state.monitor.timestamps), 3)

        # t=170.0 を追加すると 100.0, 110.0 がパージされ、120.0, 170.0 の2件が残るはず
        self.client.post("/errors", json={"timestamp": 170.0})
        time.sleep(0.1)
        self.assertEqual(len(state.monitor.timestamps), 2)


if __name__ == '__main__':
    unittest.main()
