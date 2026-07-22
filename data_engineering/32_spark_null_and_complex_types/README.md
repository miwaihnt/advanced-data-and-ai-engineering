# 課題32：PySparkにおけるNULL処理と複合データ型（JSON・Array）の展開

## 🎯 課題概要

実務のデータパイプラインやコーディング試験では、**不完全なNULL値を含むデータの補正**や、**ネストされたJSON文字列・配列（Array）型の展開**が頻繁に求められる。

本課題では、`coalesce`, `fillna`, `dropna`, および `from_json`, `explode` を用いた高度なデータパースとクレンジングを実装する。

**使用言語**: PySpark (DataFrame API & Spark SQL)

---

## 📋 前提データ

```
【ユーザー行動ログ (user_logs)】
| log_id | user_id | preferred_email | backup_email | raw_payload                                              |
|--------|---------|-----------------|--------------|----------------------------------------------------------|
| L-101  | U-01    | alice@main.com  | alice@bk.com  | '{"tags": ["tech", "ai"], "device": "mobile"}'           |
| L-102  | U-02    | NULL            | bob@bk.com   | '{"tags": ["news"], "device": "desktop"}'                |
| L-103  | U-03    | NULL            | NULL         | '{"tags": ["tech", "sports", "fashion"], "device": null}'|
| L-104  | U-04    | dave@main.com   | NULL         | NULL                                                     |
```

---

## ✅ 実装要件

### Part 1：NULL制御・フォールバック設計
- `preferred_email` が存在すればそれを使い、なければ `backup_email` を採用し、それでもなければ `"unknown@example.com"` を割り当てる `contact_email` 列を追加すること（`coalesce` を使用）。
- 連絡先メールアドレスが完全に欠損（`"unknown@example.com"`）しているレコードを除外すること（`filter` または `dropna`）。

### Part 2：JSONパースと配列のフラット化（explode）
- `raw_payload` のJSON文字列を Pyspark の `StructType` スキーマを適用してパースすること（`from_json`）。
- JSON内の `tags`（配列）を展開し、各タグごとに1行となるフラットな構造へ変換すること（`explode` または `explode_outer`）。
- デバイス情報 `device` がNULLの場合は `"unknown"` で補完すること（`fillna` または `coalesce`）。

---

## 🚀 期待するアウトプット（Part 1 & 2 適用後）

```
+------+-------+----------------+-------+---------+
|log_id|user_id|contact_email   |device |tag      |
+------+-------+----------------+-------+---------+
|L-101 |U-01   |alice@main.com  |mobile |tech     |
|L-101 |U-01   |alice@main.com  |mobile |ai       |
|L-102 |U-02   |bob@bk.com      |desktop|news     |
|L-103 |U-03   |unknown@ex.com  |unknown|tech     | ... (除外ロジック適用時はL-103は除去)
+------+-------+----------------+-------+---------+
```

---

## 💬 設計上の問い

1. `coalesce()` 関数と `fillna()` / `ifnull()` / `nvl()` の挙動と用途の違いを説明せよ。
2. `explode()` と `explode_outer()` の違いは何か？配列が `NULL` または空配列 `[]` の場合にそれぞれどのような結果になるか？
3. 大規模データに対する `explode()` 実行時の注意点（データ爆発・シャッフル・空間計算量）について述べよ。

---

## 📁 ファイル構成

```
32_spark_null_and_complex_types/
├── README.md
├── main.py          # ← ここに実装せよ
└── answer/
    └── main.py      # 正解コード
```
