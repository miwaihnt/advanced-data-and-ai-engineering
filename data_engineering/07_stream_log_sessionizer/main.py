import logging
from typing import Iterator,Any
from dataclasses import dataclass


# ===========
# config
# ===========


# ===========
# logging
# ===========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s -%(message)s'
)

logger = logging.getLogger(__name__)

# ===========
# dataclass
# ===========
@dataclass
class UserLog:
    timestamp: int  # UNIXタイムスタンプ（秒）
    user_id: str      # ユーザーID（文字列。Noneや空文字が混ざる可能性あり）

    @classmethod
    def from_dict(cls, data:dict[str, Any]) -> "UserLog":
        # 必須キーチェック
        for key in ["timestamp", "user_id"] is None:
            if not key in data:
                raise ValueError(f"必須キー{key}が見つかりません")

        uid = data["user_id"]
        timestamp = data["timestamp"]

        # 型チェック
        if not isinstance(uid, str):
            raise ValueError(f"user_idの型がstrではありません")

        # timestampをint型に変換
        try:
            int_timestamp = int(timestamp)
        except (ValueError, TypeError) as e:
            raise ValueError(f"timestampのint変換に失敗しました")

        return cls(user_id=uid, timestamp=int_timestamp)

# ===========
# 主要処理：ユーザごとにセッション集計して返すGeneretor
# 返却:{"user": "userA", "start_time": int, "end_time": int, "session_cnt": int}
# ===========
def aggregate_user_session(stream_data: Iterator[dict[str, Any]]) -> Iterator[dict[str,Any]]:
    
    # 返却するdict{"userA": {}}
    user_session = {}

    # sessionの判断時間（30分 = 1800秒）
    session_time = 1800

    # stream dataを順次処理
    for stream in stream_data:

        # dataのvalidation
        try:
            validate_data = UserLog.from_dict(stream)
        except (ValueError, TypeError) as e:
            logger.warning(f"[Skip]：データのバリデーションに失敗しました。{e}")
            continue

        uid = validate_data.user_id
        time = validate_data.timestamp

        # =====
        # 判定ロジック
        # =====

        # 対象のユーザが初回のログだった場合
        # ユーザの辞書を作る
        if uid not in user_session:
            user_session[uid] = {
                "user": uid, 
                "start_time": time, 
                "end_time": time,
                "session_cnt": 1               
            }
        else:
            # もし過去のセッションのログが混ざってきたら
            # セッションを1増加させ、過去のログは無視する
            if  time - user_session[uid]["end_time"] < 0:
                user_session[uid]["session_cnt"] += 1

            # もし前回のend_timeから30分経過していたら
            # 現在のセッション情報を返し、新しいuser sessionとしてカウントを始める
            elif session_time <= time - user_session[uid]["end_time"]:
                yield user_session[uid]
                user_session[uid] = {
                    "user": uid, 
                    "start_time": time, 
                    "end_time": time,
                    "session_cnt": 1               
                }

            # 30分以内なら
            else:
                user_session[uid]["end_time"] = time 
                user_session[uid]["session_cnt"] += 1
    
    # ループ後に残っているセッション情報を返す
    for u, d in user_session.items():
        yield d
              


def main():
    # テストデータ
    test_stream = [
        {"timestamp": 1715644800, "user_id": "user_A", "event_name": "login"},     # セッション1開始
        {"timestamp": 1715645100, "user_id": "user_A", "event_name": "view_item"}, # +5分
        {"timestamp": 1715645200, "user_id": "user_B", "event_name": "login"},     # ユーザーBセッション開始
        {"timestamp": 1715645400, "user_id": "user_A", "event_name": "click"},     # +5分（合計10分）
        {"timestamp": 1715645350, "user_id": "user_A", "event_name": "click"},     # ⚠️イジワル：逆転ログ（カウント+1、時間は不変）
        {"timestamp": 1715645400, "user_id": None, "event_name": "click"},         # ⚠️イジワル：ゴミデータ（スキップ）
        {"timestamp": 1715648000, "user_id": "user_A", "event_name": "logout"},    # 前回のAから約43分後 ➔ セッション1終了、セッション2開始
        {"timestamp": 1715649000, "user_id": "user_B", "event_name": "click"},     # ユーザーBの前回から63分後 ➔ ユーザーBのセッション終了、新規開始
    ]

    for i in aggregate_user_session(test_stream):
        print(i)


if __name__ == '__main__':
    main()









