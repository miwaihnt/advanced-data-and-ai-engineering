import logging
import bisect
from collections import defaultdict
from typing import Dict, List, Tuple

# =========
# loggingの設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TimeMap")


# ==========================================
# 【模範解答】バージョン付きKVS（TimeMap）の実装
# ==========================================
class TimeMap:
    """
    バージョン付きキーバリューストア。

    【内部データ構造の設計思想】
    self.store は以下のような辞書構造を持つ:
        {
            "config_lr": {
                "timestamps": [100, 200, 300],       # ソート済みのタイムスタンプリスト
                "values":     ["0.01", "0.001", "0.0001"]  # 同じインデックスに対応する値リスト
            }
        }
    timestamps リストは常にソート済みを維持するため、bisect_right による O(log N) の二分探索で
    「指定時刻以前の最新の値」を高速に引くことができる。
    """

    def __init__(self):
        # defaultdict を使い、未知のキーにアクセスした際に自動で空の構造を作成する
        self.store: Dict[str, Dict[str, List]] = defaultdict(
            lambda: {"timestamps": [], "values": []}
        )

    def set(self, key: str, value: str, timestamp: int) -> None:
        """
        指定されたキーに対して、タイムスタンプ付きで値を記録する。
        タイムスタンプは単調増加（常に前回より大きい値で呼ばれる）を前提とする。
        時間計算量: O(1)（リスト末尾への append）
        """
        self.store[key]["timestamps"].append(timestamp)
        self.store[key]["values"].append(value)

    def get(self, key: str, timestamp: int) -> str:
        """
        指定されたキーに対して、timestamp 以前の最新の値を返す。
        該当する値がない場合は空文字 "" を返す。
        時間計算量: O(log N)（bisect_right による二分探索）
        """
        # 1. 存在しないキーへのアクセスを安全に処理（KeyError を防ぐ）
        if key not in self.store:
            return ""

        entry = self.store[key]
        timestamps = entry["timestamps"]
        values = entry["values"]

        # 2. bisect_right を使って、timestamp 以下の最大のインデックスを探す
        # bisect_right(timestamps, timestamp) は、timestamp を挿入できる「右側」の位置を返す。
        # つまり、timestamps[i] <= timestamp を満たす最後の要素のインデックスは (挿入位置 - 1) になる。
        idx = bisect.bisect_right(timestamps, timestamp)

        # 3. idx が 0 の場合、timestamp より前にデータが一切存在しない（全履歴が未来）
        if idx == 0:
            return ""

        # 4. idx - 1 が「timestamp 以前の最新の値」のインデックス
        return values[idx - 1]


# =========
# main
# =========
def main():
    tm = TimeMap()

    # 🟢 テストケース1: 正常系（時系列データの記録と取得）
    tm.set("config_lr", "0.01", 100)
    tm.set("config_lr", "0.001", 200)
    tm.set("config_lr", "0.0001", 300)

    print("--- 🟢 テストケース1: 正常系 ---")
    assert tm.get("config_lr", 150) == "0.01", "150 時点では 0.01 であるべき"
    assert tm.get("config_lr", 200) == "0.001", "200 時点では 0.001 であるべき"
    assert tm.get("config_lr", 350) == "0.0001", "350 時点では 0.0001 であるべき"
    print(f"get('config_lr', 150) -> '{tm.get('config_lr', 150)}'")
    print(f"get('config_lr', 200) -> '{tm.get('config_lr', 200)}'")
    print(f"get('config_lr', 350) -> '{tm.get('config_lr', 350)}'")
    print("✅ 正常系テスト合格！")

    # 🔴 テストケース2: エッジケース
    print("\n--- 🔴 テストケース2: エッジケース ---")
    assert tm.get("config_lr", 50) == "", "50 時点ではデータなし"
    assert tm.get("unknown_key", 100) == "", "存在しないキー"
    print(f"get('config_lr', 50)  -> '{tm.get('config_lr', 50)}'")
    print(f"get('unknown', 100)   -> '{tm.get('unknown_key', 100)}'")
    print("✅ エッジケーステスト合格！")

    # 🟢 テストケース3: 複数キーの独立性
    print("\n--- 🟢 テストケース3: 複数キーの独立性 ---")
    tm.set("model_name", "gpt-4", 100)
    tm.set("model_name", "gpt-4o", 200)
    assert tm.get("model_name", 150) == "gpt-4"
    assert tm.get("config_lr", 150) == "0.01"  # 別キーに影響しない
    print(f"get('model_name', 150) -> '{tm.get('model_name', 150)}'")
    print(f"get('config_lr', 150)  -> '{tm.get('config_lr', 150)}'")
    print("✅ 複数キー独立性テスト合格！")


if __name__ == '__main__':
    main()
