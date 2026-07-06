import logging

# =========
# loggingの設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LRUCache")


# ==========================================
# 【課題】LRUキャッシュ（Least Recently Used Cache）の実装
# ==========================================
class LRUCache:
    """
    容量制限付きの LRU (Least Recently Used) キャッシュ。
    get と put が両方 O(1) で動作するように、
    辞書（HashMap）＋ 双方向連結リスト（Doubly Linked List）を自作して実装する。
    
    collections.OrderedDict は使用禁止。

    【要件】
    1. get(key) は O(1) で値を返す。存在しない場合は -1 を返す。
    2. put(key, value) は O(1) で値を格納する。容量超過時は LRU を追い出す。
    3. capacity = 1 でも正しく動作すること。
    """

    def __init__(self, capacity: int):
        # TODO: 内部データ構造を初期化しなさい。
        # ヒント: 辞書（dict）と、ダミーの head / tail ノードを持つ双方向連結リストを用意する。
        pass

    def get(self, key: int) -> int:
        """キーに紐づく値を返す。存在しなければ -1。アクセスされたら「最近使った」に昇格させる。"""
        # TODO: ここに実装しなさい。
        pass

    def put(self, key: int, value: int) -> None:
        """キーに値を格納する。容量超過時は LRU（最も古い）を追い出す。"""
        # TODO: ここに実装しなさい。
        pass


# =========
# main
# =========
def main():
    cache = LRUCache(capacity=2)

    # テストケース1: 正常系
    cache.put(1, 100)
    cache.put(2, 200)
    print(f"get(1) -> {cache.get(1)}")   # 期待: 100
    cache.put(3, 300)                     # 容量オーバー -> キー2を追い出し
    print(f"get(2) -> {cache.get(2)}")   # 期待: -1 (追い出し済み)
    cache.put(4, 400)                     # 容量オーバー -> キー1を追い出し
    print(f"get(1) -> {cache.get(1)}")   # 期待: -1 (追い出し済み)
    print(f"get(3) -> {cache.get(3)}")   # 期待: 300
    print(f"get(4) -> {cache.get(4)}")   # 期待: 400


if __name__ == '__main__':
    main()
