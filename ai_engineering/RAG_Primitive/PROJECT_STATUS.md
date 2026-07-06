# RAG Project Status

このドキュメントは、プロジェクトの全体進捗とタスクを管理するためのものである。
「1億件のスケール」に耐えうるアーキテクチャを実現するためのマイルストーンを定義する。

## 🎯 プロジェクトゴール
- **短期目標**: 特定の会議を Unit of Work として End-to-End で処理し、LanceDB へ格納する。
- **長期目標**: 1,000万〜1億件のチャンクを $O(1)$ の空間計算量で処理し、インデックス構築のトレードオフを定量化する。
- **Advanced Goal**: ハイブリッド検索（ベクトル + BM25）とリランキングによる、商用レベルの検索精度とスケーラビリティの両立。

---

## 📈 全体進捗 (Milestones)

- [x] **Phase 0-6: Foundations & Streaming Pipeline (STEP 1)**
    - [x] アーキテクチャ設計とモダンな開発環境 (`uv`) の構築
    - [x] ストリーミング・クローラーの実装
    - [x] 空間計算量 $O(B)$ を維持した増分書き出し (`Incremental Append`)
    - [x] `asyncio.Queue` による並行ワーカーモデル（Acquisition/Chunk/Embed/Store）の構築
    - [x] 3.5万件規模でのインデックス特性（IVF-PQ vs HNSW）の検証

- [x] **Phase 7: Hybrid Search & Reranking (STEP 2)**
    - [x] **BM25 (Full Text Search) の実装**: 特定キーワードへの再現率（Recall）向上
    - [x] **RRF (Reciprocal Rank Fusion) の統合**: ベクトルスコアと単語スコアの公平な融合
    - [x] **ローカル・リランカー (Cross-Encoder) の導入**: `sentence-transformers` による二段階検索の実現（API料金0円！）
    - [ ] **評価と最適化**: 検索レイテンシの改善と精度の定量的評価
    - [ ] **テストコードの実装**: コアロジックの単体テスト

---

## 🛠️ 現在の作業 (Current Task)
**Phase 7: Hybrid Search & Reranking (Final Polish)**
- **Progress**: `hotchpotch/japanese-reranker-cross-encoder-xsmall-v1` を用いたローカルリランク環境の構築完了。RRF の粗引きと Cross-Encoder の精査を組み合わせた 2-Stage Retrieval が動作中。
- **Next Step**: リランカーの初期化オーバーヘッドの削減、および `tests/` 内への単体テストの追加。これらが終われば、技術記事（Zenn）へのアウトプットを行う。

---

## 📝 決定事項 & ログ
- **2026-04-01**: プロジェクト開始。`uv` を採用。
- 2026-04-23: **Phase 6 完了。** ワーカーモデルへの移行により、E2E ストリーミング処理を達成。
- 2026-04-23: **STEP 2 (Phase 7) 開始。** マネージド SaaS の内部ロジックを理解するため、ハイブリッド検索の自作フェーズへ移行。
- 2026-04-24: **事前分かち書き & FTS 実装完了。** `SudachiPy` (Mode C) を用いた「事前分かち書き」をインデックス工程へ統合。LanceDB/Tantivy による全文検索の疎通を確認し、ベクトル検索との定性的な特性比較を完了。

