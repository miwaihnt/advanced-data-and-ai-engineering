# 🧠 プロジェクト・メモ：BigData Transformer

## 📝 設計上の決定事項

### 1. データ生成戦略 (2026-05-02)
- **パターン**: `asyncio.Queue` を使用した Producer-Consumer パターン。
- **理由**: CPUバウンドなデータ生成（Faker）とI/Oバウンドなファイル書き込みを分離するため。
- **バックプレッシャ（背圧）**: 512MBのメモリ制限下でOOMを防止するため、`asyncio.Queue` に `maxsize` を設定。
- **フォーマット**: Polarsでのストリーミング処理を容易にするため、NDJSON（Newline Delimited JSON）を採用。
- **チャンク化**: システムコールを最小化するため、バッチ単位での書き込みを実装。

### 2. ファイル分割（Rotation）と命名規則 (2026-05-03)
- **命名規則**: `raw_data_{run_id}_{part_id:03d}.jsonl`
    - `run_id`: 実行開始時のタイムスタンプ（例: 202605031200）。同一セッション内のファイルを識別。
    - `part_id`: 001から始まる3桁の連番。ソート可能性を担保。
- **分割基準（Threshold）**: 100MB 〜 250MB（圧縮後を見据えたサイズ）。
- **判定ロジック**: `DataConsumer` 内で書き込み済みバイト数を累積し、閾値を超えたタイミングで次のファイルへローテーション。
- **目的**: Snowflakeへの並列ロード（1スレッド=1ファイル）を最適化し、かつ生成失敗時のリスタートリスクを分散させる。

### 3. ハイブリッド・バリデーション戦略 (2026-05-04)
- **概念**: パフォーマンス（Polars/Rust）とデータ品質（Pydantic/Python）の両立。
- **実装**:
    - **第一関門 (Polars)**: `filter` を用いて、ビジネスルール（`amount >= 0`, `status` の妥当性等）に違反する「異常疑い行」を高速に抽出。
    - **第二関門 (Pydantic)**: 抽出された異常行のみを `Transaction(**row)` に通し、詳細なエラー理由（`ValidationError`）をログ出力。
    - **データ鮮度**: Silver層（集計）にはバリデーション済みのクリーンなデータのみを使用。
- **メリット**: 10GB全量をPythonオブジェクトに変換するコストを避けつつ、異常値に対してはPydanticの強力な検知能力を活用できる。

## 🚀 ロードマップ
1. [x] ジェネレータの実装 (Producer/Consumer/Engine)
2. [/] パフォーマンス・チューニング (10GB/512MB RAM) - Fakerの最適化が次の山場。
3. [x] Polarsによる変換処理の実装 (Streaming Mode)
4. [x] Pydanticバリデーションの組み込み (Hybrid方式)
5. [ ] Snowflakeロードパイプラインの構築
6. [ ] E2Eテストとモニタリングの整備

## 📊 現在のステータス (2026-05-04)
- **トランスフォーマー**: Polarsの `scan_ndjson` と `sink_parquet` を活用した、512MB制限遵守のストリーミング・パイプラインが完成。
- **バリデーション**: PydanticモデルをSource of Truthとしたスキーマ自動生成、および異常行の自動検知ロジックを統合。
- **Next Task**: 10GB生成のボトルネックであるFakerの高速化（または代替）と、Snowflakeへの `PUT/COPY` 連携。

## ⚠️ 既知の課題 / 技術的負債
- **Fakerのパフォーマンス**: `date_time_this_year` 等が依然として遅い。10GB生成には致命的。
- **二重スキャンのコスト**: 現在、Bronze（全量）とSilver（集計）でデータを2回読み込んでいる。処理時間の増大。
- **メモリ消費の理解**: Pythonオブジェクトの「脂肪」によるOOMリスク。詳細は [PYTHON_MEMORY_RESEARCH.md](./PYTHON_MEMORY_RESEARCH.md) を参照。
- **設定の硬直性**: パス計算が一部のディレクトリ構成に依存しすぎている。

## 💡 リファレンス実装戦略（理想的な回答）

### 1. データ生成 (Generation)
- **Queue Maxsize**: 5,000 〜 10,000 レコード程度。これなら辞書形式でも数MB〜数十MBに収まる。
- **Batch size**: 1回につき 10,000 レコード書き込み。システムコール削減を最優先に。
- **Fakerの最適化**: `Faker` は `product_name` などどうしても必要なものだけに絞る。`id` や `amount` は `random.Random` を使う方が圧倒的に速い。
- **再現性**: 生成ループの開始時に `random.seed(base_seed + task_id)` を設定すること。

### 2. データ変換 (Transformation)
- **ストリーミング安全な操作**: `filter`, `select`, `with_columns`, `group_by` (一部) は安全。`sort` や `pivot` はメモリに全データを乗せようとするため、ストリーミング不可。要注意。
- **Pydanticバリデーション**: 10GB全部にPydanticを通すのは「負け」。Polarsでクレンジング後に、最終結果（数千行程度）に対して適用するのが賢い Senior DE のやり方。

### 3. ロード (Loading)
- **Parquet**: 1GB程度のファイルに分割してステージングすること。Snowflakeは並列ロードが得意なので、巨大な1ファイルより分割されている方が効率が良い。
