import asyncio
import logging
from typing import AsyncIterator, Any, List

# =========
# logging設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LogMerger")

# =========
# テスト用の疑似非同期ログストリーム
# =========
class ServerStream:
    """
    指定されたログデータと遅延シミュレーションを持つ非同期イテレータ
    """
    def __init__(self, name: str, logs: List[dict[str, Any]], delays: List[float]):
        self.name = name
        self.logs = logs
        self.delays = delays
        self.index = 0

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self.index >= len(self.logs):
            raise StopAsyncIteration

        # ネットワーク遅延のシミュレーション
        delay = self.delays[self.index] if self.index < len(self.delays) else 0.1
        await asyncio.sleep(delay)

        log = self.logs[self.index]
        self.index += 1
        return log

# ==========================================
# 【模範解答】非同期K-Way Mergeマージ関数（タイムアウト制御付き）
# ==========================================
async def merge_streams_async(
    streams: List[AsyncIterator[dict[str, Any]]], 
    timeout_sec: float = 1.0
) -> AsyncIterator[dict[str, Any]]:
    """
    K本の非同期ストリームをタイムスタンプの昇順でマージして返す非同期ジェネレータ。
    """
    K = len(streams)
    queues = [asyncio.Queue(maxsize=1) for _ in range(K)]

    # 1. 各ストリームからデータを取得してキューに詰めるWorker
    # タイムアウト時に anext() がキャンセルされるのを防ぐため、Worker側ではタイムアウトを設けず愚直に待つ
    async def worker(idx: int, stream: AsyncIterator[dict[str, Any]], q: asyncio.Queue):
        try:
            while True:
                try:
                    item = await anext(stream)
                    await q.put((item, "data"))
                except StopAsyncIteration:
                    await q.put((None, "eof"))
                    break
        except Exception as e:
            logger.error(f"[Worker-{idx}] エラーが発生しました: {e}")
            await q.put((e, "error"))

    # バックグラウンドタスクとして起動
    tasks = [asyncio.create_task(worker(i, stream, queues[i])) for i, stream in enumerate(streams)]

    buffer = [None] * K
    timed_out = [False] * K
    eof = [False] * K
    last_yielded_ts = -1

    try:
        while not all(eof):
            # ① タイムアウトから復帰したストリームが、キューにデータを流し込んだかノンブロッキングで確認する
            for i in range(K):
                if timed_out[i] and not queues[i].empty():
                    payload, event_type = queues[i].get_nowait()
                    if event_type == "data":
                        buffer[i] = payload
                        timed_out[i] = False
                    elif event_type == "eof":
                        eof[i] = True
                        timed_out[i] = False
                    elif event_type == "error":
                        logger.error(f"[Error] Stream-{i} error: {payload}")
                        eof[i] = True
                        timed_out[i] = False

            # ② バッファが空で、タイムアウトもしておらず、EOFもしていないストリームからデータを取得する
            fetch_coros = []
            fetch_indices = []
            for i in range(K):
                if buffer[i] is None and not timed_out[i] and not eof[i]:
                    # キューからの取得自体にタイムアウトをかける（元のストリームのI/Oはキャンセルされない）
                    fetch_coros.append(asyncio.wait_for(queues[i].get(), timeout=timeout_sec))
                    fetch_indices.append(i)

            if fetch_coros:
                # すべての未受信バッファについて並行して待機
                results = await asyncio.gather(*fetch_coros, return_exceptions=True)
                for idx, res in zip(fetch_indices, results):
                    if isinstance(res, asyncio.TimeoutError):
                        logger.warning(
                            f"[Timeout] Stream-{idx} is non-responsive for {timeout_sec}s. "
                            "Skipping temporarily to avoid blocking."
                        )
                        timed_out[idx] = True
                    elif isinstance(res, Exception):
                        logger.error(f"[Error] Stream-{idx} failed: {res}")
                        eof[idx] = True
                    else:
                        payload, event_type = res
                        if event_type == "data":
                            buffer[idx] = payload
                        elif event_type == "eof":
                            eof[idx] = True
                        elif event_type == "error":
                            logger.error(f"[Error] Stream-{idx} payload error: {payload}")
                            eof[idx] = True

            # ③ すべてのバッファが空で、かつまだ稼働中のストリームがある場合（全ストリームがタイムアウト状態など）
            # どれか1つのストリームが復帰するまでブロックして待つ
            if all(b is None for b in buffer) and not all(eof):
                active_indices = [i for i in range(K) if not eof[i]]
                if active_indices:
                    pending_tasks = {
                        asyncio.create_task(queues[i].get()): i for i in active_indices
                    }
                    done, pending = await asyncio.wait(
                        pending_tasks.keys(),
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    # 完了しなかったタスクはキャンセル
                    for t in pending:
                        t.cancel()

                    for t in done:
                        idx = pending_tasks[t]
                        try:
                            payload, event_type = t.result()
                            if event_type == "data":
                                buffer[idx] = payload
                                timed_out[idx] = False
                            elif event_type == "eof":
                                eof[idx] = True
                            elif event_type == "error":
                                eof[idx] = True
                        except Exception:
                            eof[idx] = True
                continue

            # ④ バッファされているデータの中から、最も古い（tsが最小）ログを選択して yield する
            next_idx = -1
            min_ts = float('inf')

            for i in range(K):
                if buffer[i] is not None:
                    if buffer[i]["ts"] < min_ts:
                        min_ts = buffer[i]["ts"]
                        next_idx = i

            if next_idx != -1:
                selected_log = buffer[next_idx]
                buffer[next_idx] = None  # バッファを消費

                # Late Data（遅延データ）のチェック
                if selected_log["ts"] < last_yielded_ts:
                    logger.warning(
                        f"[Late Data] Received delayed data from Stream-{next_idx}: {selected_log} "
                        f"(Last yielded timestamp: {last_yielded_ts})"
                    )
                else:
                    last_yielded_ts = selected_log["ts"]

                yield selected_log

    finally:
        # Workerタスクの確実なクリーンアップ
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


# =========
# テスト実行コード
# =========
async def main():
    # 1. テストストリームの設定
    # サーバーBの2件目のデータ（ts=108）の受信時に 2.5秒 の遅延を発生させる
    stream_a = ServerStream(
        name="Server-A",
        logs=[
            {"ts": 100, "server": "Server-A", "val": "A_1"},
            {"ts": 105, "server": "Server-A", "val": "A_2"},
            {"ts": 110, "server": "Server-A", "val": "A_3"}
        ],
        delays=[0.1, 0.1, 0.1]
    )

    stream_b = ServerStream(
        name="Server-B",
        logs=[
            {"ts": 102, "server": "Server-B", "val": "B_1"},
            {"ts": 108, "server": "Server-B", "val": "B_2"},  # 2.5秒遅延！
            {"ts": 112, "server": "Server-B", "val": "B_3"}
        ],
        delays=[0.1, 2.5, 0.1]
    )

    stream_c = ServerStream(
        name="Server-C",
        logs=[
            {"ts": 101, "server": "Server-C", "val": "C_1"},
            {"ts": 104, "server": "Server-C", "val": "C_2"}
        ],
        delays=[0.1, 0.1]
    )

    streams = [stream_a, stream_b, stream_c]

    logger.info("======= 非同期マージテスト開始 =======")
    
    # タイムアウト閾値を 1.0秒 に設定して実行
    async for merged_log in merge_streams_async(streams, timeout_sec=1.0):
        logger.info(f"[OUTPUT] {merged_log}")

    logger.info("======= 非同期マージテスト終了 =======")

if __name__ == "__main__":
    asyncio.run(main())
