# 💻 Advanced Data & AI Engineering Lab

本リポジトリは、本番環境（Production-grade）におけるデータエンジニアリングおよびLLMエージェントシステムの実装パターンを検証するための技術ラボです。
大規模データ統合パイプラインや自律エージェントの設計における、高度な計算量最適化、非同期並行処理、および耐障害性の設計パターンを網羅しています。

---

## 🗺️ リポジトリ構成

本リポジトリは、データエンジニアリングの堅牢性（DE）とAIの社会実装（AI）の架け橋となるよう、2つの主要な領域に整理されています。

### 📁 [data_engineering](./data_engineering/)
低レイヤーのアルゴリズム、省メモリ処理、大規模データパイプラインのためのインフラ制御パターン。
- **主な検証項目**:
  - `heapq` を用いた省メモリK-Way Merge（空間計算量 $O(K)$） ｜ [Code](./data_engineering/09_memory_efficient_merge/answer/main.py)
  - スレッドを用いないアクセス時間差ベースの Token Bucket レートリミッター ｜ [Code](./data_engineering/12_token_bucket_rate_limiter/)
  - `asyncio` を用いた高スループットな非同期 K-Way Merge ｜ [Code](./data_engineering/13_async_k_way_merge/answer/main.py)
  - `deque` による $O(1)$ 移動窓集計 ｜ [Code](./data_engineering/10_sliding_window_aggregator/answer/main.py)
  - `bisect` による時系列検索（TimeMap） ｜ [Code](./data_engineering/11_cursor_pagination_wrapper/answer/main.py)
  - $O(1)$ 計算量のカスタムLRUキャッシュ実装 ｜ [Code](./data_engineering/20_custom_lru_cache/answer/main.py)

### 📁 [ai_engineering](./ai_engineering/)
LLMの物理限界を突破し、プロダクションレベルのAI応用システムを設計するための実装パターン。
- **主な検証項目**:
  - ReActモデルを応用した自己修復（Self-Correction）機能付きAIエージェント ｜ [Code](./ai_engineering/24_resumable_self_healing_agent/main.py)
  - 状態管理（シリアライズ）と途中再開（Resumability）による耐障害性エージェント設計 ｜ [Code](./ai_engineering/24_resumable_self_healing_agent/answer/main.py)
  - マルチエージェント討論によるコンセンサスアルゴリズム ｜ [Code](./ai_engineering/21_multi_agent_debate/answer/main.py)
  - 正規表現・Pydanticを用いたロバストな構造化出力抽出 ｜ [Code](./ai_engineering/16_pydantic_llm_parser/answer/main.py)
  - 意味論的セマンティックチャンキングと並行埋め込み生成 ｜ [Code](./ai_engineering/23_semantic_chunking_embedding/answer/main.py)

---

## 📈 開発ステータスとレビューログ

各課題の進捗状況や、シニアエンジニアリング視点での設計判断・自己フィードバックは、[development_log.md](./development_log.md) に記録・管理されています。

---

## ⚙️ 動作環境
- **Language**: Python 3.11+
- **LLM Run**: Ollama (qwen2.5:3b)
