import logging
from typing import List, Tuple, Dict, Set

# =========
# loggingの設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RRFMerger")


# ==========================================
# 【模範解答】RRF (Reciprocal Rank Fusion) マージアルゴリズムの実装
# ==========================================
def compute_rrf(
    rankings: List[List[str]], 
    k: int = 60
) -> List[Tuple[str, float]]:
    """
    複数の検索システムのランキング結果を相互順位融合 (RRF) に基づいて統合し、
    (ドキュメントID, RRFスコア) の降順リストを返す。
    """
    # 1. 堅牢な入力バリデーション（Fail-Fast）
    if k < 0:
        raise ValueError(f"平滑化定数 k は0以上の整数である必要があります。入力値: {k}")

    if not rankings:
        return []

    # ドキュメントIDごとの統合RRFスコアを蓄積するハッシュマップ
    rrf_scores: Dict[str, float] = {}

    # 2. 各検索システムの結果をイテレート
    for system_idx, ranking in enumerate(rankings):
        seen_in_current_list: Set[str] = set()

        for position, doc_id in enumerate(ranking):
            # 防御的設計: ドキュメントIDの型/空チェック
            if not isinstance(doc_id, str) or not doc_id.strip():
                raise ValueError(
                    f"システム {system_idx} の位置 {position} に不正なドキュメントIDを検知しました。"
                )

            # 防御的設計: 同一リスト内での重複チェック
            # 実務上、検索システム側のバグで同じIDが複数回返ってくることがある。
            # その場合は、最初に出現した順位（＝より高い順位）のみを採用して重複はスキップする。
            if doc_id in seen_in_current_list:
                logger.warning(
                    f"[重複検知] システム {system_idx} の検索結果内でID '{doc_id}' が重複しています。"
                    f"最初に出現した順位（高順位）を優先し、この出現は無視します。"
                )
                continue
            seen_in_current_list.add(doc_id)

            # 3. 1-indexed の順位を算出
            rank = position + 1
            
            # RRF数式: 1 / (k + rank)
            reciprocal_rank_score = 1.0 / (k + rank)
            
            # 既存のスコアがあれば加算（一方のリストにしか存在しない場合も get() で安全に 0.0 フォールバック）
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + reciprocal_rank_score

    # 4. RRFスコアの降順（高い順）でソート
    # 計算量: ユニークドキュメント数を N とすると O(N log N)
    sorted_rankings = sorted(
        rrf_scores.items(), 
        key=lambda item: item[1], 
        reverse=True
    )

    return sorted_rankings


# =========
# main
# =========
def main():
    logger.info("Starting RRF Search Results Merger...")
    
    # 🟢 テストケース1: 正常系（BM25とVector検索のハイブリッドマージ）
    bm25_results = ["doc_A", "doc_B", "doc_C"]
    vector_results = ["doc_B", "doc_D", "doc_A"]
    
    # 🔴 テストケース2: 重複ドキュメントや不正データを含む異常系シミュレーション
    dirty_results = [
        ["doc_A", "doc_B", "doc_A"],  # 同一結果内に "doc_A" が重複
        ["doc_B", "", "doc_D"]        # 空文字の不正なIDを含む
    ]
    
    print("\n--- 🟢 テストケース1: 正常系のマージ実行 ---")
    try:
        merged_results = compute_rrf([bm25_results, vector_results], k=60)
        for doc_id, score in merged_results:
            print(f"Document: {doc_id}, RRF Score: {score:.6f}")
        
        # 検証用の簡易チェック
        assert merged_results[0][0] == "doc_B", "1位は doc_B であるべきです"
        assert merged_results[1][0] == "doc_A", "2位は doc_A であるべきです"
        print("✅ 正常系の検証結果は完璧よ！")
        
    except Exception as e:
        logger.error(f"テストケース1でエラーが発生しました（バグ）: {e}", exc_info=True)

    print("\n--- 🔴 テストケース2: 異常系（重複・汚いデータ）の実行 ---")
    try:
        # 空文字が含まれているため、バリデーションで ValueError を投げて安全に停止（Fail-Fast）するはず
        compute_rrf(dirty_results, k=60)
    except ValueError as e:
        print(f"🔥 狙い通りにシステムが安全に爆死（Fail-Fast完了）:\n{e}")


if __name__ == '__main__':
    main()
