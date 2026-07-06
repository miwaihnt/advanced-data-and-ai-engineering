import logging
from typing import Dict, Optional

# =========
# loggingの設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LRUCache")


# ==========================================
# 【模範解答】LRUキャッシュ（Least Recently Used Cache）の実装
# ==========================================

class Node:
    """
    双方向連結リスト（Doubly Linked List）のノード。

    【なぜ「双方向」が必要なのか？】
    ノードを削除する際に、前後のポインタ（prev / next）を繋ぎ替える必要がある。
    「単方向（next だけ）」だと、削除対象のノードの「前のノード」を知るために
    先頭からリストを走査（O(N)）する必要が生じてしまう。
    双方向なら、node.prev で O(1) で前のノードにアクセスできるため、
    削除が O(1) で完結する。
    """
    __slots__ = ['key', 'value', 'prev', 'next']  # メモリ最適化

    def __init__(self, key: int = 0, value: int = 0):
        self.key = key
        self.value = value
        self.prev: Optional['Node'] = None
        self.next: Optional['Node'] = None


class LRUCache:
    """
    容量制限付きの LRU (Least Recently Used) キャッシュ。

    【内部データ構造の設計思想】

    1. 辞書（HashMap）: key -> Node のマッピング
       キーから O(1) でノードの「場所」を引くための索引。

    2. 双方向連結リスト: 使用順序の管理
       - head（ダミー） <-> 最近使ったノード <-> ... <-> 最も古いノード <-> tail（ダミー）
       - 「最近使った」ノードは head の直後に移動させる。
       - 「最も古い（LRU）」ノードは tail の直前にいる。
       - 容量超過時は tail の直前のノードを O(1) で削除する。

    【なぜ head / tail にダミーノードを使うのか？】
    ダミーノードがないと、「リストが空の時」「要素が1つだけの時」に
    head や tail が None になるケースを毎回 if 分岐でチェックする必要があり、
    コードが複雑化してバグの温床になる。
    ダミーノードを番兵（Sentinel）として置くことで、常に head.next と tail.prev が
    有効なノードであることが保証され、境界条件の処理が不要になる。
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: Dict[int, Node] = {}

        # ダミーの head / tail ノード（番兵）を作成し、相互に接続
        self.head = Node()  # ダミー head（最近使われた側）
        self.tail = Node()  # ダミー tail（最も古い側）
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: Node) -> None:
        """
        双方向連結リストからノードを O(1) で削除する。
        前後のポインタを繋ぎ替えるだけで、ノード自体はメモリ上に残る（再利用可能）。
        """
        prev_node = node.prev
        next_node = node.next
        prev_node.next = next_node
        next_node.prev = prev_node

    def _add_to_front(self, node: Node) -> None:
        """
        ノードを head の直後（＝最近使われた位置）に O(1) で挿入する。

        挿入前: head <-> first_node <-> ...
        挿入後: head <-> node <-> first_node <-> ...
        """
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def _move_to_front(self, node: Node) -> None:
        """
        既存のノードを「最近使われた」位置（head直後）に移動する。
        「削除して先頭に再挿入」の2ステップで実現。
        """
        self._remove(node)
        self._add_to_front(node)

    def get(self, key: int) -> int:
        """
        キーに紐づく値を返す。存在しなければ -1。
        アクセスされたノードは「最近使った」位置に昇格させる。
        時間計算量: O(1)
        """
        if key not in self.cache:
            return -1

        node = self.cache[key]
        # アクセスされた = 「最近使った」ので、リストの先頭に移動
        self._move_to_front(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        """
        キーに値を格納する。
        - すでにキーが存在する場合: 値を上書きし、先頭に移動。
        - 新規キーの場合: 新しいノードを作成して先頭に追加。
          容量超過時は tail 直前の LRU ノードを追い出す。
        時間計算量: O(1)
        """
        if key in self.cache:
            # 既存キーの値を更新し、先頭に移動
            node = self.cache[key]
            node.value = value
            self._move_to_front(node)
        else:
            # 新規ノードを作成
            new_node = Node(key, value)
            self.cache[key] = new_node
            self._add_to_front(new_node)

            # 容量超過チェック
            if len(self.cache) > self.capacity:
                # LRU（最も古い）ノード = tail の直前のノードを追い出す
                lru_node = self.tail.prev
                self._remove(lru_node)
                del self.cache[lru_node.key]  # 辞書からも削除


# =========
# main
# =========
def main():
    # 🟢 テストケース1: 基本動作（LeetCode 146 の公式テストケース）
    print("--- 🟢 テストケース1: 基本動作 ---")
    cache = LRUCache(capacity=2)
    cache.put(1, 100)
    cache.put(2, 200)
    assert cache.get(1) == 100, "キー1は100であるべき"
    print(f"get(1) -> {cache.get(1)}")  # 100

    cache.put(3, 300)  # 容量オーバー -> キー2(LRU)を追い出し
    assert cache.get(2) == -1, "キー2は追い出されたはず"
    print(f"get(2) -> {cache.get(2)}")  # -1

    cache.put(4, 400)  # 容量オーバー -> キー1(LRU)を追い出し
    assert cache.get(1) == -1, "キー1は追い出されたはず"
    assert cache.get(3) == 300
    assert cache.get(4) == 400
    print(f"get(1) -> {cache.get(1)}")  # -1
    print(f"get(3) -> {cache.get(3)}")  # 300
    print(f"get(4) -> {cache.get(4)}")  # 400
    print("✅ テストケース1 合格！")

    # 🟢 テストケース2: 値の上書き
    print("\n--- 🟢 テストケース2: 値の上書き ---")
    cache2 = LRUCache(capacity=2)
    cache2.put(1, 100)
    cache2.put(2, 200)
    cache2.put(1, 999)  # キー1の値を上書き（追い出しは発生しない）
    assert cache2.get(1) == 999, "キー1は999に上書きされたはず"
    assert cache2.get(2) == 200, "キー2は健在のはず"
    print(f"get(1) -> {cache2.get(1)}")  # 999
    print(f"get(2) -> {cache2.get(2)}")  # 200
    print("✅ テストケース2 合格！")

    # 🟢 テストケース3: capacity = 1 のエッジケース
    print("\n--- 🟢 テストケース3: capacity = 1 ---")
    cache3 = LRUCache(capacity=1)
    cache3.put(1, 100)
    assert cache3.get(1) == 100
    cache3.put(2, 200)  # 容量オーバー -> キー1を追い出し
    assert cache3.get(1) == -1, "キー1は追い出されたはず"
    assert cache3.get(2) == 200
    print(f"get(1) -> {cache3.get(1)}")  # -1
    print(f"get(2) -> {cache3.get(2)}")  # 200
    print("✅ テストケース3 合格！")

    # 🟢 テストケース4: get による順序昇格の検証
    print("\n--- 🟢 テストケース4: getによる順序昇格 ---")
    cache4 = LRUCache(capacity=2)
    cache4.put(1, 100)
    cache4.put(2, 200)
    cache4.get(1)       # キー1にアクセス -> キー1が「最近使った」に昇格
    cache4.put(3, 300)  # 容量オーバー -> キー2がLRU（キー1はgetで昇格済み）なので追い出し
    assert cache4.get(2) == -1, "キー2が追い出されるべき（キー1はgetで昇格済み）"
    assert cache4.get(1) == 100, "キー1はgetで昇格済みなので健在"
    print(f"get(2) -> {cache4.get(2)}")  # -1
    print(f"get(1) -> {cache4.get(1)}")  # 100
    print("✅ テストケース4 合格！")

    print("\n🎉 全テストケース合格！")


if __name__ == '__main__':
    main()
