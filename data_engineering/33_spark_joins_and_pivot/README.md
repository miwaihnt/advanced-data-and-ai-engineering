# 課題33：SparkにおけるJoin最適化（Broadcast Join）とPivot（縦横変換）

## 🎯 課題概要

分散コンピューティングにおいて、テーブル結合（Join）は最もコストの高い「Shuffle（ネットワーク再配置）」を引き起こす要因となる。小大規模テーブルの結合では **Broadcast Join** の採用が鉄則である。

本課題では、**Broadcast Join** による結合最適化と、集計結果をクロス集計表示する **Pivot（縦横変換）** を実装する。

**使用言語**: PySpark (DataFrame API & Spark SQL)

---

## 📋 前提データ

```
【大容量トランザクション (sales_df)】
| transaction_id | user_id | store_id | category    | amount |
|----------------|---------|----------|-------------|--------|
| TX-001         | U-01    | ST-101   | Electronics | 50000  |
| TX-002         | U-02    | ST-102   | Books       | 2000   |
| TX-003         | U-01    | ST-101   | Books       | 1500   |
| TX-004         | U-03    | ST-101   | Electronics | 120000 |
| TX-005         | U-02    | ST-101   | Clothing    | 8000   |

【小容量店舗マスタ (stores_df)】
| store_id | store_name  | region |
|----------|-------------|--------|
| ST-101   | Tokyo Flag  | Kanto  |
| ST-102   | Osaka Main  | Kansai |
```

---

## ✅ 実装要件

### Part 1：Broadcast Join の最適化
- `stores_df` は十分に小規模（マスタテーブル）であるため、`pyspark.sql.functions.broadcast()` を指定して `sales_df` と Left Join すること。
- 不要なシャッフルを回避し、`region` 情報（関東/関西）を付与すること。

### Part 2：GroupBy + Pivot（クロス集計）
- 結合後のデータを用い、地域（`region`）ごとに、カテゴリ（`category`）ごとの売上合計額（`amount` の sum）を算出する Pivot テーブルを作成すること。
- 欠損値（売上がないカテゴリ）は `0` に補完すること（`fillna(0)`）。

---

## 🚀 期待するアウトプット（Part 2）

```
+-------+-----------+-----+--------+
|region |Electronics|Books|Clothing|
+-------+-----------+-----+--------+
|Kanto  |170000     |1500 |8000    |
|Kansai |0          |2000 |0       |
+-------+-----------+-----+--------+
```

---

## 💬 設計上の問い

1. **Broadcast Hash Join (BHJ)** の動作原理を説明せよ。なぜ小規模テーブルにのみ適用可能で、どのような場合に OOM (Out Of Memory) リスクが生じるか？
2. Sparkにおけるデフォルトの Broadcast 閾値（`spark.sql.autoBroadcastJoinThreshold`）のサイズはいくつか？
3. `Left Semi Join` と `Left Anti Join` の違いと、どのようなユースケースで利用されるか説明せよ。

---

## 📁 ファイル構成

```
33_spark_joins_and_pivot/
├── README.md
├── main.py          # ← ここに実装せよ
└── answer/
    └── main.py      # 正解コード
```
