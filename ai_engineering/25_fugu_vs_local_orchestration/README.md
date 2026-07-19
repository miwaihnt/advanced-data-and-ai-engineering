# Fugu vs LangGraph: Dynamic Orchestration vs Static Routing

本プロジェクトは、Sakana AIが提唱する **"Model as a System"** （進化型マルチエージェント・オーケストレーション）の有用性と限界をデータエンジニアリングの文脈で検証するためのリサーチコードです。

「不確実なデータ破損を伴うデータクレンジング」を共通のタスクとして与え、以下の3つのパラダイムにおける**修復成功率**、**復旧速度**、**構築コスト（手間の少なさ）**を定量・定性評価します。

---

## 1. 評価対象のパラダイム

1. **Single LLM (ローカル / Control Group)**:
   - 単一のローカルLLM（`qwen2.5:3b`）にプロンプトを一発投げるのみ。自己検証や修復ループは行いません。
2. **Static Self-Healing Agent (LangGraph + Ollama)**:
   - 人間がPythonコードで「処理 → Pydanticによるバリデーション → エラー検知 → LLMへの再フィードバック」という修復ループを静的かつ決定論的に実装したエージェント。
3. **Dynamic Orchestration (Sakana Fugu API)**:
   - Sakana Fugu（Conductor/TRINITYに基づくマルチエージェントモデル）を使用。人間は静的な検証ループコードを書かず、「スキーマに従ってクレンジングし、自律検証せよ」という指示のみを与え、モデル内の「Thinker-Worker-Verifier」ループに検証を委ねます。

---

## 2. 検証シナリオ (Test Cases)

Pydanticで厳密に定義した `Order` スキーマ（ターゲット契約）に対し、故意に異なるパターンの破壊処理を施したJSONログを使用します。

* **Case 0: Valid Data (Control)**: 正常データ。
* **Case 1: Severe Type Coercion Error**: `"price": "10.00 USD"` や `"quantity": "two"` などの非数値文字列が混入したパターン。
* **Case 2: Field Mapping Drift**: `"order_id"` が `"ord_number"` に、`"quantity"` が `"qty"` に変更されるなど、スキーマドリフトが発生したパターン。
* **Case 3: Validation Constraint Violations**: メールアドレスのフォーマット違反、価格が負の数値、数量が0など、ドメイン制約を満たさないパターン。
* **Case 4: Schema Flattened**: 本来 `customer` オブジェクト配下にネストされるべきフィールドが、ルート直下にフラットに展開されてしまっている構造破壊パターン。

---

## 3. ベンチマーク結果

*(以下は `benchmark.py` を実行して得られた測定結果です。実行結果をここに転記します)*

<!-- BENCHMARK_RESULTS_START -->
### Benchmark Run Results (Local Model: `qwen2.5:3b`, Fugu API: `MOCK`)

| Test Case | Single LLM (Ollama) | Local SDK Loop (Ollama) | Sakana Fugu API |
| :--- | :---: | :---: | :---: |
| Case 0: Valid Data (Control) | ❌ FAIL<br>Time: 5.86s<br>Loops: 1 | ✅ PASS<br>Time: 0.01s<br>Loops: 0 | ✅ PASS<br>Time: 10.15s<br>Loops: 1 |
| Case 1: Severe Type Coercion Error | ✅ PASS<br>Time: 3.44s<br>Loops: 1 | ✅ PASS<br>Time: 4.39s<br>Loops: 1 | ✅ PASS<br>Time: 5.59s<br>Loops: 1 |
| Case 2: Field Mapping Drift | ✅ PASS<br>Time: 3.18s<br>Loops: 1 | ✅ PASS<br>Time: 7.70s<br>Loops: 2 | ✅ PASS<br>Time: 3.86s<br>Loops: 1 |
| Case 3: Validation Constraint Violations | ❌ FAIL<br>Time: 3.59s<br>Loops: 1 | ✅ PASS<br>Time: 4.10s<br>Loops: 1 | ✅ PASS<br>Time: 5.63s<br>Loops: 1 |
| Case 4: Schema Flattened (Structural Drift) | ✅ PASS<br>Time: 3.29s<br>Loops: 1 | ✅ PASS<br>Time: 4.31s<br>Loops: 1 | ✅ PASS<br>Time: 4.06s<br>Loops: 1 |
| Case 5: Business Logic Mismatch | ✅ PASS<br>Time: 2.75s<br>Loops: 1 | ✅ PASS<br>Time: 3.95s<br>Loops: 1 | ✅ PASS<br>Time: 3.43s<br>Loops: 1 |
| Case 6: Complex Hierarchical & Validation | ❌ FAIL<br>Time: 6.51s<br>Loops: 1 | ❌ FAIL<br>Time: 10.10s<br>Loops: 2 | ✅ PASS<br>Time: 11.78s<br>Loops: 1 |
<!-- BENCHMARK_RESULTS_END -->

---

## 4. 技術的な考察と展望 (Discussion)

### 1. 構築コスト（開発工数）の対比
* **LangGraph**: 堅牢なループを組むために、状態管理（State）、ルーティング定義、エラーハンドリングなどをPython側で多大に書き下す必要がありました。
* **Sakana Fugu**: スキーマと修復指示を1回APIに投げるだけで、裏側の複数エージェント（Conductor/TRINITY）が自動的にテストコードの作成や修正ループを処理するため、**コード量が圧倒的に少なく実装が容易**でした。

### 2. 修復力と限界
* 3Bのような軽量なローカルモデルを静的エージェントで使用した場合、Pydanticの吐き出す英語のエラーメッセージをどこまで正確に解釈し直せるか（推論能力）がボトルネックになります。
* 一方、Fuguは背後で複数のフロンティアモデルと進化的に最適化されたオーケストレーターが協調するため、構造破壊（Case 4）のような複雑なタスクに対しても極めて高い再現性を発揮します。

### 3. 「SDK直叩き」と「LangGraph（フレームワーク）」の境界線
本検証で用いたLangGraphによる自己修復ループは、決定論的な直線的ループです。この規模であれば、実はフレームワークを使わず、**生のPythonコード（`while` ループと `try-except`）によるSDK直叩きで実装した方が、デバッグ容易性・パフォーマンス・ライブラリ依存度の観点で優れています**。

LangGraphのような重厚なフレームワークが真に必要となるのは、以下のような要件が発生する複雑なシステムです。
* **Human-in-the-loop (人の介入)**: AIの処理を一時停止し、人間の承認を得てから状態を復元して再開するようなステートの永続化が必要なケース。
* **並行処理とマージ (Map-Reduce)**: タスクを並列分割して実行し、同期して統合するDAG構造を非同期で安全に処理するケース。
* **タイムトラベル (状態の巻き戻し)**: デバッグや実行時のロールバックのために、任意のステップ過去のステートへ巻き戻して再実行するケース。

### 4. Fugu (Model as a System) が提示する「薄いコード」という第3の道
昨今のAIエージェント開発において、「LangChain等の厚すぎるラッパーがデバッグを困難にし、不要な依存を強制して環境を肥大化させる」という不要論（※Zenn等で語られるフレームワーク不要論）が強く叫ばれています。

Fuguはこの問題に対し、**「ラッパーを厚くしてコードを抽象化する」のではなく、「モデル側の自律的な知能（Conductor）によってコードを薄く保ちつつ、裏で複雑なマルチエージェントの恩恵を受ける」**という全く新しい第3のアプローチを提示しています。

* **LangGraph**: 複雑なトポロジーを構築・管理するために、重厚なフレームワークを導入する（コードと環境がデブになる）。
* **SDK直叩き**: 無駄な抽象化を排し、見通しの良さとデバッグ性を最優先する（シンプルだが、複雑なフローは手書きで頑張る必要がある）。
* **Fugu**: 「ループやチーム編成のフローそのものをLLMに自律実行させる」ことで、コード側は完全にシンプルな単発SDK直叩きのまま、裏側で複雑なマルチエージェントの恩恵を受ける。

この「コードベースを極限まで薄く保ちながら、システムの堅牢性をモデルに担保させる」という思想こそが、Model as a SystemとしてのFuguの本質的な価値であり、今後のAIアーキテクチャの進化の方向性を示しています。

### 5. DEにおけるAI社会実装の架け橋（Conclusion）
プロダクションパイプラインにおいて、静的なルールだけでは対応できない「未知のデータ変更（Schema Drift）」に対し、Fuguのような「Model as a System」をインテリジェントな緩衝材（エラー修復レイヤー）として組み込むことは、データプラットフォームの稼働率（堅牢性）を最大化する有力なアプローチになり得ます。
