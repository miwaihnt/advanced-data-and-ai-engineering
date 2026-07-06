import logging

# =========
# loggingの設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TimeMap")


# ==========================================
# 【課題】バージョン付きKVS（TimeMap）の実装
# ==========================================
class TimeMap:
    """
    バージョン付きキーバリューストア。
    set(key, value, timestamp) で値を記録し、
    get(key, timestamp) で指定時刻以前の最新値を O(log N) で取得する。
    """

    def __init__(self):
        # TODO: 内部データ構造を初期化しなさい。
        pass

    def set(self, key: str, value: str, timestamp: int) -> None:
        """指定されたキーに対して、タイムスタンプ付きで値を記録する。"""
        # TODO: ここに実装しなさい。
        pass

    def get(self, key: str, timestamp: int) -> str:
        """指定されたキーに対して、timestamp 以前の最新の値を返す。該当なしなら空文字。"""
        # TODO: ここに実装しなさい（bisect モジュールの活用を推奨）。
        pass


# =========
# main
# =========
def main():
    tm = TimeMap()

    # テストケース1: 正常系（時系列データの記録と取得）
    tm.set("config_lr", "0.01", 100)
    tm.set("config_lr", "0.001", 200)
    tm.set("config_lr", "0.0001", 300)

    print("--- 🟢 テストケース1: 正常系 ---")
    print(f"get('config_lr', 150) -> '{tm.get('config_lr', 150)}'")   # 期待: "0.01"
    print(f"get('config_lr', 200) -> '{tm.get('config_lr', 200)}'")   # 期待: "0.001"
    print(f"get('config_lr', 350) -> '{tm.get('config_lr', 350)}'")   # 期待: "0.0001"

    print("\n--- 🔴 テストケース2: エッジケース ---")
    print(f"get('config_lr', 50)  -> '{tm.get('config_lr', 50)}'")    # 期待: "" (データなし)
    print(f"get('unknown', 100)   -> '{tm.get('unknown', 100)}'")     # 期待: "" (キーなし)


if __name__ == '__main__':
    main()
