# 課題29：Spark SQL ウィンドウ関数による重複排除とTop-Nランキング

## 🎯 課題概要

大規模な注文テーブルには、同一注文が複数回インジェストされる「重複レコード」が発生することがある。
本課題では、**ウィンドウ関数を用いた純粋SQLによる重複排除**と、**カテゴリ別 Top-N 抽出**を実装する。

**使用言語**: PySpark（DataFrame API）および Spark SQL の両方で実装すること。

---

## 📋 前提データ

```
orders テーブル:
| order_id | customer_id | product_id | category  | amount  | ordered_at          |
|----------|-------------|------------|-----------|---------|---------------------|
| ORD-001  | C-01        | P-A        | Electronics | 59800 | 2024-01-05 10:00:00 |
| ORD-001  | C-01        | P-A        | Electronics | 59800 | 2024-01-05 10:00:00 |  ← 重複
| ORD-002  | C-02        | P-B        | Books     |  1500   | 2024-01-06 11:00:00 |
| ORD-003  | C-01        | P-C        | Electronics| 12000  | 2024-01-07 09:30:00 |
| ORD-004  | C-03        | P-D        | Books     |  2800   | 2024-01-08 14:00:00 |
| ORD-005  | C-02        | P-E        | Electronics| 98000  | 2024-01-09 16:45:00 |
| ORD-005  | C-02        | P-E        | Electronics| 98000  | 2024-01-09 16:45:00 |  ← 重複
| ORD-006  | C-03        | P-F        | Books     |  5500   | 2024-01-10 13:20:00 |
```

---

## ✅ 実装要件

### Part 1：重複排除（Deduplication）
- `ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY ordered_at)` を使い、各 `order_id` の中で最初の1件のみを残す。
- `filter(rn == 1)` で重複行を取り除くこと。
- **PySpark DataFrame API** と **Spark SQL (spark.sql())** の両方で実装すること。

### Part 2：カテゴリ別売上 Top-N ランキング
- 重複排除済みデータを使い、カテゴリ (`category`) ごとに `amount` 降順で順位を付ける。
- `DENSE_RANK()` を使い、同額の場合は同じ順位を付与すること。
- 引数 `top_n: int = 2` を受け取り、各カテゴリの上位 N 件を返す関数を実装すること。

---

## 🚀 期待するアウトプット

```
=== Part 1: 重複排除後のレコード（6件） ===
+--------+-----------+----------+-----------+------+-------------------+
|order_id|customer_id|product_id|category   |amount|ordered_at         |
+--------+-----------+----------+-----------+------+-------------------+
|ORD-001 |C-01       |P-A       |Electronics|59800 |2024-01-05 10:00:00|
|ORD-002 |C-02       |P-B       |Books      |1500  |2024-01-06 11:00:00|
...（重複 ORD-001, ORD-005 は1件のみ）
+--------+-----------+----------+-----------+------+-------------------+

=== Part 2: カテゴリ別 Top-2（DENSE_RANK） ===
+-----------+--------+------+----+
|category   |order_id|amount|rank|
+-----------+--------+------+----+
|Books      |ORD-006 |5500  |1   |
|Books      |ORD-004 |2800  |2   |
|Electronics|ORD-005 |98000 |1   |
|Electronics|ORD-001 |59800 |2   |
+-----------+--------+------+----+
```

---

## 💬 設計上の問い

1. `ROW_NUMBER()` と `RANK()` と `DENSE_RANK()` の挙動の違いを説明せよ。特に、同じ値が複数存在する場合にどう変わるか？
2. ウィンドウ関数は内部的にデータのシャッフル（Shuffle）を引き起こす。`PARTITION BY customer_id` でパーティションを切ったとき、特定の `customer_id` に注文が極端に集中している場合（Data Skew）、どのような問題が生じ、どう対策するか？
3. 本課題のような重複排除を**Delta Lakeの `MERGE INTO`** で実装した場合と、ウィンドウ関数+`filter` で実装した場合のトレードオフを論じよ。

---

## ⚠️ 分散環境におけるアーキテクチャ上の注意点（Performance & Memory Caveats）

1. **`df.collect()` による Driver ノードの OOM（Out Of Memory）リスク**
   - `collect()` は各 Worker ノードに分散保持されている全パーティションデータを、単一の Driver ノードのメモリ上に集約（Action）する。
   - 数億〜数拾億件規模のデータに対して実行すると Driver ノードのメモリが即座にパンクしてクラッシュするため、動作確認には必ず `show(N)` や `take(N)`、または集計処理を適用すること。

2. **`PARTITION BY` が引き起こすシャッフル（Shuffle）オーバーヘッド**
   - ウィンドウ関数や GroupBy で `PARTITION BY customer_id` を指定すると、同一キーを持つデータがネットワークを経由して特定の Worker ノードへ集約される（Shuffle）。
   - シャッフルはディスクI/Oとネットワーク通信を伴う分散処理中最も高コストな操作であるため、不要なパーティション分割の抑制や、特定キーへのデータ集中（Data Skew）に対するサルト（Salting）技法の適用を検討すること。

---

## 📁 ファイル構成

```
29_spark_window_deduplication/
├── README.md
├── main.py          # ← ここに実装せよ
└── answer/
    └── main.py      # 正解コード
```
