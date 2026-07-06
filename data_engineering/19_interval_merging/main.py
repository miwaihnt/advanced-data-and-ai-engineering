import logging
from typing import List, Tuple

# =========
# loggingの設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntervalMerger")


# ==========================================
# 【課題】重複する時間区間のマージ（Interval Merging）
# ==========================================
def merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    重複する時間区間をマージし、統合後の区間リストを返す。

    【要件】
    1. 時間計算量 O(N log N) で解くこと。
    2. 空リストが渡された場合は空リストを返すこと。
    3. 完全に包含される区間を正しく処理すること。
    4. 隣接する区間（境界が一致する）はマージ対象とすること。
    """
    # TODO: ここにインターバルマージロジックを実装しなさい。
    pass


# =========
# main
# =========
def main():
    logger.info("Starting Interval Merger...")

    # テストケース1: 正常系（重複あり）
    intervals_1 = [(1, 3), (2, 6), (8, 10), (15, 18)]
    result_1 = merge_intervals(intervals_1)
    print(f"テスト1（重複あり）: {result_1}")
    # 期待: [(1, 6), (8, 10), (15, 18)]

    # テストケース2: 完全包含
    intervals_2 = [(1, 10), (3, 5), (4, 7)]
    result_2 = merge_intervals(intervals_2)
    print(f"テスト2（完全包含）: {result_2}")
    # 期待: [(1, 10)]

    # テストケース3: 隣接（境界が接する）
    intervals_3 = [(1, 3), (3, 5), (5, 7)]
    result_3 = merge_intervals(intervals_3)
    print(f"テスト3（隣接）    : {result_3}")
    # 期待: [(1, 7)]

    # テストケース4: 重複なし
    intervals_4 = [(1, 2), (5, 6), (9, 10)]
    result_4 = merge_intervals(intervals_4)
    print(f"テスト4（重複なし）: {result_4}")
    # 期待: [(1, 2), (5, 6), (9, 10)]

    # テストケース5: 空リスト
    intervals_5 = []
    result_5 = merge_intervals(intervals_5)
    print(f"テスト5（空リスト）: {result_5}")
    # 期待: []


if __name__ == '__main__':
    main()
