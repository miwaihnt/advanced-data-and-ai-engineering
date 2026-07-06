# 🚀 Project: 10GB NDJSON Transformer (under 512MB RAM)

## 📌 概要
このプロジェクトは、リソース制限（メモリ512MB）という極限状態で、10GBの巨大なJSONデータ（API出力を想定）を生成・変換・集計する、データエンジニアリング（DE）の実践課題である。

目標は、**「ただ動くコード」ではなく「Tier 1/2企業で通用する堅牢で高速なデータパイプライン」**を構築すること。

## 🎯 達成目標
- **Pythonプロフェッショナリズム**: `asyncio` による高速I/O処理の実証。
- **リソース最適化**: PolarsのStreaming APIを用いたOut-of-core処理の完遂。
- **データ品質の担保**: Pydantic v2を用いたスキーマ定義と、型安全なデータ変換。
- **オブザーバビリティ**: 処理中のメモリ使用量・スループットの可視化。

## 🛠 技術スタック
- **Data Engine**: [Polars](https://pola.rs/) (LazyFrame & Streaming Mode)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Concurrency**: `asyncio` (for data generation)
- **Monitoring**: `psutil`, `tqdm`
- **Quality**: `ruff`, `pytest`

## 📂 構成案 (Suggested Architecture)
- `generator.py`: `asyncio` + `Faker` による高速ダミーデータ生成ツール。
- `transformer.py`: Polars Streaming APIを用いたメイン集計ロジック。
- `models.py`: Pydanticによるデータモデル定義と、Polars Schemaへのマッピング。
- `monitor.py`: メモリ消費量を監視するデコレータ・ユーティリティ。

## 📊 挑戦状：512MB RAMの壁
1. 10GBのデータを `scan_ndjson` で読み込む。
2. 特定のキーで `group_by` し、集計（平均・合計・カウント）を行う。
3. Pydanticで定義したバリデーションを、パフォーマンスを落とさずに組み込む。
4. **結果を1分以内に（環境によるが）メモリを溢れさせずに出力する。**
