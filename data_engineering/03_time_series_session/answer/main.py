import logging
import json
from collections import defaultdict
from typing import Iterable, Iterator, Any
from pathlib import Path
from dataclasses import dataclass

# =========
# config
# =========
# スクリプトの場所を基準にパスを設定することで、どこから実行しても安全にするわ
TEST_DATA_PATH = Path(__file__).parent.parent / "input/input.jsonl"

# =========
# logging
# 正しいフォーマット属性 %(name)s を使用
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========
# dataclass
# イミュータブル (frozen=True) にして、かつ型ヒントを厳密にしたわよ
# =========
@dataclass(frozen=True)
class UserLog:
    user_id: str
    time_minutes: int  # キャスト後の型に合わせる

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserLog":
        # 面接でも手抜きせず、最低限のキーチェックを実行
        for key in ["user_id", "time"]:
            if key not in data:
                raise ValueError(f"Missing required key: '{key}'")

        uid = data["user_id"]
        time_str = data["time"]

        if not isinstance(uid, str) or not isinstance(time_str, str):
            raise ValueError("Data fields must be of string type")

        # 時刻パースと簡単なバリデーション
        try:
            h_str, m_str = time_str.split(":")
            h, m = int(h_str), int(m_str)
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError(f"Time values out of range: {time_str}")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format (expected HH:MM): {time_str}") from e

        minutes = h * 60 + m
        return cls(user_id=uid, time_minutes=minutes)

# =========
# ユーザごとにstream_logを集約する関数
# =========
def aggregate_log(stream_data: Iterable[dict[str, Any]]) -> dict[str, list[int]]:
    stream_log = defaultdict(list)
    for data in stream_data:
        try:
            valid_data = UserLog.from_dict(data)
            stream_log[valid_data.user_id].append(valid_data.time_minutes)
        except ValueError as e:
            # バリデーションエラー時はスキップしてログを吐くのがDEの鉄則よ！
            logger.warning(f"[Skip] Invalid record skipped: {e}. Raw data: {data}")
    return stream_log

# =========
# sessionをユーザごとにカウントする関数
# =========
def session_count(user_data: dict[str, list[int]]) -> dict[str, int]:
    user_session = {}

    for user, times in user_data.items():
        # 元データをソート
        times.sort()
        
        session_cnt = 0
        before_time = -float('inf')  # 最初のアクセスが何時でもセッションを開始させるため、負の無限大で初期化

        for current_time in times:
            if before_time + 30 <= current_time:
                session_cnt += 1
            before_time = current_time

        user_session[user] = session_cnt

    return user_session

# =========
# テストデータをファイルから読み込み返すGenerator
# =========
def stream_jsonl(test_path: Path) -> Iterator[dict[str, Any]]:
    if not test_path.is_file():
        raise FileNotFoundError(f"Target file not found at: {test_path}")

    with open(test_path, "r", encoding="utf-8") as f:
        for index, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as e:
                logger.warning(f"[Skip] Line {index}: JSON decode failed. Error: {e}")
            except Exception as e:
                logger.error(f"[Skip] Line {index}: Unexpected error: {e}", exc_info=True)

def main():
    logger.info("======= Process Started =======")
    try:
        aggregate_data = aggregate_log(stream_jsonl(TEST_DATA_PATH))
        result = session_count(aggregate_data)
        logger.info("======= Process Finished =======")
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Process failed: {e}", exc_info=True)

if __name__ == '__main__':
    main()
