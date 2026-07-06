import logging
import heapq
from typing import Iterator, Any, List, Dict, Tuple
from dataclasses import dataclass

# =======
# loggingの設定
# =======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =======
# データ検証用のDataclass
# =======
@dataclass
class ServerLog:
    ts: int
    val: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerLog":
        # 必須キーの存在チェック
        for key in ["ts", "val"]:
            if key not in data or data[key] is None:
                raise ValueError(f"必須キー '{key}' が不足しているか、Nullです")
        
        ts_raw = data["ts"]
        val_raw = data["val"]

        # 型チェック
        if not isinstance(val_raw, str):
            raise TypeError("val は str型 である必要があります")

        # timestampの安全な数値キャスト
        try:
            ts_int = int(ts_raw)
        except (ValueError, TypeError) as e:
            raise ValueError(f"timestamp の数値変換に失敗しました: {e}")

        return cls(ts=ts_int, val=val_raw)


# =======
# メイン処理：K-Way Merge による省メモリなストリーミング合流
# =======
def process_stream_data(stream_data: List[Iterator[Dict[str, Any]]]) -> Iterator[Dict[str, Any]]:
    """
    各サーバーのイテレータから最小限のメモリ(常にサーバー台数分 K件)でデータをマージし、
    完璧なタイムスタンプ昇順のストリームとして yield する。
    """
    # 💡 タプルの構造は (ts, stream_index, raw_log) にする！
    # 理由: Pythonはタプル同士を比較するとき、先頭の要素から順に比較するわ。
    # もし (ts, raw_log, stream_index) にしてしまうと、タイムスタンプが完全に一致したときに
    # 2番目の要素である辞書（raw_log）同士を比較しようとして「TypeError: '<' not supported between 'dict' and 'dict'」でクラッシュするの！
    # index（整数）を2番目に挟むことで、ts重複時はindexの比較で解決させ、辞書比較を絶対に発生させないのがプロの技術よ。
    min_heap: List[Tuple[int, int, Dict[str, Any]]] = []

    # ==========================================
    # 1. 初期化：各ストリームから最初の1件だけを取り出して heap に入れる
    # ==========================================
    for index, server_stream in enumerate(stream_data):
        while True:
            try:
                # ⭕️ ループではなく next() で最初の1件だけを引き抜く！
                server_log = next(server_stream)
                validate_data = ServerLog.from_dict(server_log)
                
                # 有効なデータであればヒープに追加して、次のサーバーへ進む
                heapq.heappush(min_heap, (validate_data.ts, index, server_log))
                break
            except StopIteration:
                # このサーバーのログストリームが最初から空だった場合はスルーして次へ
                break
            except (ValueError, TypeError) as e:
                # バリデーションエラーが起きたら、警告を出して「同じストリームの次の一行」を再試行する
                logger.warning(f"[Skip]: 初期化データのバリデーション失敗: {e}")
                continue

    # ==========================================
    # 2. ループ：heapにデータがある限り、最古をpopし、該当ストリームから1件補充する
    # ==========================================
    while min_heap:
        # 最もタイムスタンプが古いログを取り出して下流へ yield する
        ts, index, server_log = heapq.heappop(min_heap)
        yield server_log

        # ポップされたデータの出身サーバー（stream_data[index]）から次の1件を補充する
        while True:
            try:
                next_log = next(stream_data[index]) # ⭕️ 1件だけnext()で引き抜く！
                validate_data = ServerLog.from_dict(next_log)
                
                # 正常データならヒープに補充して、ループを抜けて次のpopへ進む
                heapq.heappush(min_heap, (validate_data.ts, index, next_log))
                break
            except StopIteration:
                # ストリームが枯渇（終了）した場合は、補充を行わずにループを抜ける（マージ継続）
                break
            except (ValueError, TypeError) as e:
                # 補充データが不正な場合は、警告ログを出して「同じストリームのさらなる次の一行」を読みに行く
                logger.warning(f"[Skip]: 補充データのバリデーション失敗: {e}")
                continue


# =======
# エントリーポイント
# =======
def main():
    # 3本のストリーム（イテレータのリスト）
    logs = [
        iter([{"ts": 100, "val": "A_1"}, {"ts": 105, "val": "A_2"}, {"ts": 110, "val": "A_3"}]),
        iter([{"ts": 102, "val": "B_1"}, {"ts": 108, "val": "B_2"}]),
        # ⚠️ 同一タイムスタンプ（101）を含むテスト
        iter([{"ts": 101, "val": "C_1"}, {"ts": 101, "val": "C_2"}])
    ]

    print("--- 🚀 K-Way Merge ストリーミング開始 ---")
    for log in process_stream_data(logs):
        print(log)
    print("--- 処理完了 ---")


if __name__ == '__main__':
    main()
