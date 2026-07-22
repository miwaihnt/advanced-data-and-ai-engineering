# 課題30：Delta Lake MERGE INTO による SCD Type 2 実装

## 🎯 課題概要

データウェアハウスにおける**緩やかに変化するディメンション（Slowly Changing Dimension / SCD）** の中でも、「Type 2」は変更履歴を全て保持する手法で、Databricks の現場で最も頻出の実装パターンの一つである。

本課題では、Delta Lake の `MERGE INTO` 構文を用いて、**顧客マスタテーブルのSCD Type 2更新**を実装する。

**使用言語**: Spark SQL（`spark.sql()` または `DeltaTable.merge()`）

---

## 📋 前提データ

```
【既存のDeltaテーブル（customers_scd2）】
| customer_id | name    | email              | is_current | valid_from | valid_to   |
|-------------|---------|---------------------|------------|------------|------------|
| C-01        | Alice   | alice@old.com       | true       | 2024-01-01 | 9999-12-31 |
| C-02        | Bob     | bob@example.com     | true       | 2024-01-01 | 9999-12-31 |

【新しく届いたデータ（更新バッチ）】
| customer_id | name    | email              |
|-------------|---------|---------------------|
| C-01        | Alice   | alice@new.com       | ← C-01のメールが変更された
| C-03        | Charlie | charlie@example.com | ← 新規顧客
```

---

## ✅ 実装要件

### SCD Type 2 の MERGEロジック

以下の3ケースを **1つの `MERGE INTO` 文で** 処理すること（注：Spark SQLの `MERGE INTO` は複数の `WHEN MATCHED` 節を持てる）。

1. **既存レコードが更新された場合（WHEN MATCHED AND 変更あり）**:
   - 旧レコードの `is_current` を `false` に、`valid_to` を「更新日（今日の日付）」にUPDATEする。

2. **更新されたレコードの新バージョンを挿入（WHEN NOT MATCHED BY TARGET）**:
   - `is_current = true`、`valid_from = 今日`、`valid_to = '9999-12-31'` で新レコードをINSERTする。

3. **完全な新規顧客の場合（WHEN NOT MATCHED BY TARGET）**:
   - ケース2と同様にINSERT。

> **注意**: Spark SQL の `MERGE INTO` は「変更ありの場合のUPDATE」と「新規INSERTを1文にまとめるのが難しい」ため、`WHEN MATCHED THEN UPDATE`（旧レコードの無効化）と `WHEN NOT MATCHED THEN INSERT`（新バージョンの追加）を**ステージングテーブルを使った2フェーズ** で実装することが許容される。

---

## 🚀 期待するアウトプット（MERGE後のDeltaテーブル）

```
| customer_id | name    | email               | is_current | valid_from | valid_to   |
|-------------|---------|---------------------|------------|------------|------------|
| C-01        | Alice   | alice@old.com       | false      | 2024-01-01 | 2024-02-01 | ← 旧レコード（無効化）
| C-01        | Alice   | alice@new.com       | true       | 2024-02-01 | 9999-12-31 | ← 新バージョン
| C-02        | Bob     | bob@example.com     | true       | 2024-01-01 | 9999-12-31 | ← 変化なし
| C-03        | Charlie | charlie@example.com | true       | 2024-02-01 | 9999-12-31 | ← 新規追加
```

---

## 💬 設計上の問い

1. Delta Lake の Time Travel（`VERSION AS OF` や `TIMESTAMP AS OF`）を使って、MERGE実行前のテーブルの状態に巻き戻す方法を説明せよ。これはどのような運用シーンで役立つか？
2. SCD Type 1（上書き更新）と Type 2（履歴保持）、Type 3（直前の値のみ保持）のトレードオフを、DWHのストレージコストとクエリの利便性の観点から比較せよ。
3. `MERGE INTO` はAtomicな操作だが、非常に大きなテーブルで実行する場合の性能上のボトルネックは何か？ `Z-Ordering` や `OPTIMIZE` はどのような役割を果たすか？

---

## 📁 ファイル構成

```
30_delta_lake_scd2_merge/
├── README.md
├── main.py          # ← ここに実装せよ
└── answer/
    └── main.py      # 正解コード
```
