# TechTrendWatcher 🚀

GitHubのトレンドリポジトリを自動で収集し、Notionで管理、Snowflakeで分析するデータパイプライン。

## 🎯 プロジェクトの目的
Pythonの高度な機能を活用し、実戦的なデータエンジニアリングスキルを習得する。
- 非同期処理による並列実行 (`asyncio`, `httpx`)
- 堅牢なバリデーションと型定義 (`Pydantic`)
- 高速なデータ加工 (`Polars`)
- 外部APIとの連携とレート制限・リトライ制御 (`tenacity`, Notion/Snowflake SDK)

## 🏗️ システムアーキテクチャ

### 1. Data Flow
1.  **Extraction**: `httpx` を用い、GitHub API から "GraphRAG" や "MCP" などの特定キーワードで非同期にリポジトリを検索。
2.  **Validation**: `Pydantic` で取得データをバリデーション。
3.  **Transformation**: `Polars` で前回データとの差分（Star増加数など）を計算。Snowflake用には `pyarrow` / `pandas` を経由して型を調整。
4.  **Loading**: 
    - **Snowflake (Silver Layer)**: `snowpark` を使用し、生データ (VARIANT) を含むトレンド情報をバルクロード。
    - **Notion**: 「今週の注目」リポジトリを自動でページ作成・更新（Upsert）。

### 2. 技術スタック & 学習トピック
- **Network**: `httpx` (Async HTTP Client)
- **Validation**: `Pydantic v2` (ConfigDict, Model Validator による生データ保持)
- **Data Processing**: `Polars` (DataFrame), `Pandas` (Snowpark連携用)
- **Database**: `Snowflake` (Snowpark SDK, write_pandas), `Notion API`
- **Infrastructure**: `uv` (Python package manager)
- **Async Strategy**: `asyncio.gather` (並列実行), `asyncio.to_thread` (同期SDKの非同期化)

## 🛠️ 開発ロードマップ
- [x] Phase 0: プロジェクトの初期化 & 環境構築
- [x] Phase 1: GitHub API 連携 (Async Search & Validation)
- [x] Phase 2: データバリデーション & Polars による差分計算
- [x] Phase 3: Notion / Snowflake 連携 (Loading)
    - [x] Notion データベースとの接続と Upsert ロジックの実装
    - [x] `asyncio.gather` による Notion 連携の並列実行
    - [x] Snowflake (Snowpark) へのバルクロード処理の実装
    - [x] **Engineering Challenges Overcome**:
        - `asyncio.to_thread` による Snowpark (同期) の非同期ラップ
        - `pyarrow` / `pandas` 依存関係の解消と型変換（TIMESTAMP_NTZ）
        - Pydantic モデルによる「生データ保持」と「フィルタリング」のトレードオフ解決
        - Snowflake 権限（USAGE/CREATE STAGE）と大文字小文字（Identifier）の制御
- [x] Phase 4: CI/CD & 定期実行の自動化
    - [x] GitHub Actions (`astral-sh/setup-uv`) による定期実行スケジュールの設定 (Cron)
    - [x] GitHub Secrets / Variables によるセキュアな認証情報管理（Notion/Snowflake/GitHub PAT）
    - [x] `uv run ttw` 用のエントリポイント整備と GitHub 仮想環境での動作確認
- [ ] Phase 5: 品質向上 & 堅牢化 (Engineering Excellence)
    - [x] **Testing**: `pytest` による網羅的テストの実装
        - [x] **Unit Tests**: `Processor` (star_delta計算) / `Models` (バリデーション/生データ保持) のテスト完了
        - [x] **Integration Tests**: `respx` を用いた `GithubClient` / `NotionClient` の異常系とリトライロジックの検証完了
        - [ ] **E2E Tests**: テスト専用環境 (Notion/Snowflake) を用いたパイプライン全体の疎通確認
        - [x] **Coverage**: 重要ロジックのカバレッジ強化 (テスト実行時間 0.2s 以下を達成)
    - [x] **Error Handling**: `tenacity` による高度なリトライ戦略（カスタム述語、リトライログ、包まれた例外の深層チェック）
    - [x] **Static Analysis**: `Ruff` と `Mypy` による厳格な品質管理（マジックナンバー排除、Pythonicな真偽値判定）
    - [x] **Documentation**: 全ての関数・クラスへの Type Hints 厳密化と Docstring 整備
    - [x] **Observability**: `structlog` を用いた JSON 形式の構造化ロギング導入
        - [x] イベント名（snake_case）とコンテキストデータの明確な分離
        - [x] 全コンポーネント（GitHub/Notion/Snowflake）のログを統一形式へ移行
        - [x] ログによる処理件数やエラーの可視化を達成
    - [x] **Engineering Excellence 修業 (completed)**:
        - `NotionClient` / `SnowflakeClient` の適切な例外移行
        - `tenacity` を活用した「賢いリトライ」と爆速なリトライテスト環境の構築
        - Snowflake の詳細なエラーコード（errno）判別と構造化ログ出力の実装
        - Snowflake の大文字小文字（Identifier）問題の解決とパイプライン完遂
        - 構造化ロギングによる運用監視基盤の確立

### 📅 今後の展望 (Future Improvements)
- [ ] **E2E Testing**: GitHub Actions 上での定期的なサンドボックス環境疎通確認
- [ ] **Metrics**: `structlog` の出力を集計し、処理件数や実行時間を時系列で可視化するダッシュボード構築
- [ ] **Performance**: 並列実行のさらなる最適化と、Polars による大量データ処理のベンチマーク

## 🚀 Advanced Engineering: 抽象化と多角化 (Review Phase)
プロジェクトの復習とさらなる高み（Tier 1レベル）を目指し、以下の高度なリファクタリングを実施。

### 1. 抽出層の抽象化 (Abstraction)
- **ABC (Abstract Base Class)**: `BaseTrendSource` を導入し、GitHub 以外のデータソース（Reddit, Hacker News等）を容易に追加できるプラグイン形式のアーキテクチャへ移行。
- **OCP (Open-Closed Principle)**: 既存の `main.py` を修正することなく、新しい Client を追加できる「拡張に開き、修正に閉じた」設計を実証。

### 2. データの正規化 (Normalization)
- **Domain Model**: 各プラットフォーム固有のデータ構造を `TrendItem` という共通モデルに変換（正規化）して保持。
- **Benefit**: プロセッサやデータロード層が特定のプラットフォームの仕様に依存しない「疎結合」な設計を実現。

### 3. モックによる拡張性検証
- **Mocking**: `RedditMockClient` を実装し、外部 API が未完成の状態でもデータパイプライン全体の挙動を検証できる開発フローを確立。

## 🤝 Agent Interaction Policy
このプロジェクトでは、Gemini CLIを「単なるコード生成ツール」ではなく、「厳しいシニアエンジニア（メンター）」として扱います。
- **教育優先**: スキル向上のため、Agentによる直接のファイル修正は最小限に留め、コードレビューや設計のアドバイスを優先します。
- **コードの所有権**: 最終的な実装は必ず人間（mew）が行い、Agentの指摘を理解した上で反映させます。
- **ツンデレ・レビュー**: 厳しい指摘の中に愛（技術的妥当性）があることを理解し、プロフェッショナルなエンジニアを目指します。

