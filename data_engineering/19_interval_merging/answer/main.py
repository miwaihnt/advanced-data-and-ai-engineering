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
# 【模範解答】重複する時間区間のマージ（Interval Merging）
# ==========================================
def merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    重複する時間区間をマージし、統合後の区間リストを返す。

    【アルゴリズム: Sort + Sweep（ソート＋スイープライン）】
    1. 入力リストを開始時刻（start）でソートする -> O(N log N)
    2. ソート済みリストを先頭から順にスキャン（sweep）していく -> O(N)
    3. 現在の区間の start が、直前にマージした区間の end 以下なら重複 -> マージ
    4. そうでなければ、新しい独立区間として結果リストに追加する

    時間計算量: O(N log N) (ソートがボトルネック)
    空間計算量: O(N) (結果リスト)
    """
    # 1. ガード節: 空リストまたは要素1つのリストはそのまま返す
    if len(intervals) <= 1:
        return list(intervals)  # 元のリストを破壊しないようコピーして返す

    # 2. 開始時刻（タプルの0番目）でソート
    # sorted() は新しいリストを返すため、元のリスト intervals を破壊しない（非破壊的）
    sorted_intervals = sorted(intervals, key=lambda x: x[0])

    # 3. 結果リストの初期化（最初の区間を「現在のマージ対象」としてセット）
    merged: List[Tuple[int, int]] = [sorted_intervals[0]]

    # 4. 2番目の区間から順にスイープ（走査）
    for current_start, current_end in sorted_intervals[1:]:
        # 直前にマージ済みの区間の終了時刻を取得
        last_merged_start, last_merged_end = merged[-1]

        if current_start <= last_merged_end:
            # 【重複 or 隣接 or 完全包含】
            # 現在の区間の start が、直前の区間の end 以下であれば、
            # 2つの区間は重なっている（または隣接している）。
            # マージするには、end の大きい方を採用する。
            #
            # 例1: (1,3) と (2,6) -> (1, max(3,6)) = (1,6)  [重複]
            # 例2: (1,3) と (3,5) -> (1, max(3,5)) = (1,5)  [隣接]
            # 例3: (1,10) と (3,5) -> (1, max(10,5)) = (1,10) [完全包含]
            merged[-1] = (last_merged_start, max(last_merged_end, current_end))
        else:
            # 【重複なし】
            # 現在の区間は、直前の区間と全く重なっていない。
            # 独立した新しい区間として結果リストに追加する。
            merged.append((current_start, current_end))

    return merged


# =========
# main
# =========
def main():
    logger.info("Starting Interval Merger...")

    # 🟢 テストケース1: 正常系（重複あり）
    intervals_1 = [(1, 3), (2, 6), (8, 10), (15, 18)]
    result_1 = merge_intervals(intervals_1)
    assert result_1 == [(1, 6), (8, 10), (15, 18)], f"テスト1失敗: {result_1}"
    print(f"✅ テスト1（重複あり）: {result_1}")

    # 🟢 テストケース2: 完全包含
    intervals_2 = [(1, 10), (3, 5), (4, 7)]
    result_2 = merge_intervals(intervals_2)
    assert result_2 == [(1, 10)], f"テスト2失敗: {result_2}"
    print(f"✅ テスト2（完全包含）: {result_2}")

    # 🟢 テストケース3: 隣接（境界が接する）
    intervals_3 = [(1, 3), (3, 5), (5, 7)]
    result_3 = merge_intervals(intervals_3)
    assert result_3 == [(1, 7)], f"テスト3失敗: {result_3}"
    print(f"✅ テスト3（隣接）    : {result_3}")

    # 🟢 テストケース4: 重複なし
    intervals_4 = [(1, 2), (5, 6), (9, 10)]
    result_4 = merge_intervals(intervals_4)
    assert result_4 == [(1, 2), (5, 6), (9, 10)], f"テスト4失敗: {result_4}"
    print(f"✅ テスト4（重複なし）: {result_4}")

    # 🟢 テストケース5: 空リスト
    intervals_5 = []
    result_5 = merge_intervals(intervals_5)
    assert result_5 == [], f"テスト5失敗: {result_5}"
    print(f"✅ テスト5（空リスト）: {result_5}")

    # 🟢 テストケース6: ソートされていない入力
    intervals_6 = [(8, 10), (1, 3), (15, 18), (2, 6)]
    result_6 = merge_intervals(intervals_6)
    assert result_6 == [(1, 6), (8, 10), (15, 18)], f"テスト6失敗: {result_6}"
    print(f"✅ テスト6（未ソート）: {result_6}")

    # 🟢 テストケース7: 元のリストが破壊されていないことを確認（非破壊性）
    original = [(8, 10), (1, 3)]
    _ = merge_intervals(original)
    assert original == [(8, 10), (1, 3)], "元のリストが破壊されている！"
    print(f"✅ テスト7（非破壊性）: 元のリストは変更されていません -> {original}")

    print("\n🎉 全テストケース合格！")


if __name__ == '__main__':
    main()
