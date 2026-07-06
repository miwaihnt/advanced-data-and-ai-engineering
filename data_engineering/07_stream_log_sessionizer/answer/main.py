import logging
import time
from typing import Iterator, Any, Dict, Optional, Iterable
from dataclasses import dataclass

# ===========
# loggingの設定
# ===========  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===========
# dataclass ＆ バリデーション
# ===========  
@dataclass
class UserLog:
    timestamp: int
    user_id: str
    event_name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserLog":
        # 1. 必須キーの存在 ＆ Nullチェック (event_nameも含めるのが安全よ)
        # ["timestamp", "user_id"] と個別の文字列に切り分けること！
        for key in ["timestamp", "user_id", "event_name"]:
            if key not in data or data[key] is None:
                raise ValueError(f"必須キー {key} がないか、またはNullです")
        
        uid = data["user_id"]
        ts_raw = data["timestamp"]
        event = data["event_name"]

        # 2. 型チェック ＆ 値チェック
        if not isinstance(uid, str) or uid.strip() == "":
            raise ValueError("user_id は空ではない文字列である必要があります")
        
        # timestampをint型へ安全にキャスト
        try:
            to_timestamp = int(ts_raw)
        except (TypeError, ValueError) as e:
            raise ValueError(f"timestamp の数値変換に失敗しました: {e}")
        
        # 3. 引数をすべて指定してインスタンスを生成して返す！
        return cls(timestamp=to_timestamp, user_id=uid, event_name=event)


# ===========
# 関数：ストリーミング・ログのセッショナイズ
# ===========  
def process_stream_log(stream_data: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    # 各ユーザーの「現在進行中のアクティブセッション」を保持する辞書
    # 構造: { user_id: { "user_id": str, "session_start": int, "session_end": int, "event_count": int } }
    active_sessions: Dict[str, dict[str, Any]] = {}
    
    # 30分（1800秒）のセッション閾値
    SESSION_TIMEOUT = 1800

    for data in stream_data:
        # バリデーション
        try:
            valid_log = UserLog.from_dict(data)
        except ValueError as e:
            logger.warning(f"[Skip]: バリデーションエラーが発生しました。原因: {e}")
            # エラー時は直ちに次のログ処理へ進む（ここが超重要！）
            continue

        uid = valid_log.user_id
        ts = valid_log.timestamp

        # パターンA: ユーザーの初回セッション開始
        if uid not in active_sessions:
            active_sessions[uid] = {
                "user_id": uid,
                "session_start": ts,
                "session_end": ts,
                "event_count": 1
            }
        
        # パターンB: すでにアクティブセッションが存在する場合
        else:
            session = active_sessions[uid]

            # 1. 到着遅れ（Out-of-order）による時間の逆転ログ
            if ts < session["session_end"]:
                # セッション期間中のカウントのみを増やし、時間は変更しない
                session["event_count"] += 1

            # 2. セッションタイムアウト（30分以上の空白）
            elif ts - session["session_end"] >= SESSION_TIMEOUT:
                # 確定した古いセッションを外へ排出 (yieldする)
                yield session

                # 今回のログを起点に、新しいセッションを初期化
                active_sessions[uid] = {
                    "user_id": uid,
                    "session_start": ts,
                    "session_end": ts,
                    "event_count": 1
                }

            # 3. 通常のセッション継続（30分以内の連続イベント）
            else:
                session["session_end"] = ts
                session["event_count"] += 1

    # ストリーム終了時、メモリに残っている未出力のセッションをすべて吐き出す
    for uid, remaining_session in active_sessions.items():
        yield remaining_session


# ===========
# エントリーポイント
# ===========  
def main():
    test_log = [
        {"timestamp": 1715644800, "user_id": "user_A", "event_name": "login"},     # セッション1開始
        {"timestamp": 1715645100, "user_id": "user_A", "event_name": "view_item"}, # +5分
        {"timestamp": 1715645200, "user_id": "user_B", "event_name": "login"},     # ユーザーBセッション開始
        {"timestamp": 1715645400, "user_id": "user_A", "event_name": "click"},     # +5分（合計10分）
        {"timestamp": 1715645350, "user_id": "user_A", "event_name": "click"},     # ⚠️イジワル：逆転ログ
        {"timestamp": 1715645400, "user_id": None, "event_name": "click"},         # ⚠️イジワル：ゴミデータ
        {"timestamp": 1715648000, "user_id": "user_A", "event_name": "logout"},    # 前回のAから約43分後 ➔ セッション1確定・排出
        {"timestamp": 1715649000, "user_id": "user_B", "event_name": "click"},     # ユーザーB前回から63分後 ➔ Bのセッション確定・排出
    ]

    print("--- 確定セッションの出力結果 ---")
    # イテレータをループに渡し、yieldされる結果を順次受け取る
    for session in process_stream_log(test_log):
        print(session)


if __name__ == '__main__':
    main()
