# 課題16：Pydanticによる不完全なLLM出力JSONの修復と構造化バリデーション (Robust LLM Ingestion Pipeline)

### 【ビジネス背景・お題】
あなたはAI機能を組み込んだFinTechSaaSのFDE（Forward Deployed Engineer）です。
顧客のチャット履歴や請求書画像からLLM（大規模言語モデル）を用いて取引データを抽出し、基幹システムに自動登録するパイプラインを開発しています。

しかし、本番環境のLLM APIは非常に気まぐれです。
- マークダウンのコードブロック（` ```json ... ``` `）で囲んで出力してくる。
- 出力の途中でトークン制限に達し、末尾の閉じ括弧（`}`）が欠損する。
- 数値のはずの金額を `"1,500"` や `"1500.00 JPY"` などの不適切なフォーマットの文字列で出力する。
- 通貨コードを `"usd"` のように小文字で出力する。

これらの不完全なJSON文字列が流れてきた際、パイプラインをクラッシュさせることなく、**正規表現や文字列操作による自動修復（Auto-Healing）**と、**Pydanticによる厳格なスキーマ検証（Schema Validation）**を行い、どうしても修復できない不正データのみを**DLQ（Dead Letter Queue：デッドレターキュー）**へ隔離する、堅牢なデータインジェクション（流し込み）処理を構築しなさい。

---

### 🚨 面接官がチェックする極限状態の要件：

1. **LLM出力JSONの自動修復ロジック（Auto-Healing）の実装:**
   `json.loads()` にかける前に、以下のパターンの崩れたJSONを文字列操作や正規表現で自動修復しなさい。
   - 前後に付与されたマークダウンブロック（` ```json ` や ` ``` `）の除去。
   - JSONの前後にある不要な説明テキスト（プレアンブル/ポストアンブル）のトリミング（最初の `{` から最後の `}` までを抽出）。
   - 末尾の閉じ括弧 `}` の欠損に対する自動補完（簡易的な修復試行）。

2. **Pydantic v2モデルを用いた構造化とカスタム検証:**
   Pydantic v2 の `BaseModel` を定義し、以下のバリデーションおよびクリーニングを実行しなさい。
   - `transaction_id`: `str`（必須。`tx_` から始まる文字列であること。満たさない場合はエラー）。
   - `user_id`: `str`（必須。`usr_\d+` の正規表現パターンにマッチすること）。
   - `amount`: `float`（必須。正の実数であること。文字列で渡された場合も数値にパース・変換できること）。
   - `currency`: `str`（必須。ISO 4217規格に準拠する3文字の英大文字。小文字で入ってきた場合は**自動で大文字に正規化（例: `usd` -> `USD`）**し、`USD`, `JPY`, `EUR`, `GBP` のいずれかであること）。
   - `timestamp`: `datetime`（必須。ISO 8601フォーマットの文字列を自動で `datetime` オブジェクトにキャストする）。

3. **DLQ（Dead Letter Queue）パターンの適用:**
   パイプラインを途中で落とさない（`try-except` による徹底した防御）。
   - 正常にパース・検証できたレコードは `Success` リストへ格納する。
   - パースエラー、またはPydanticのバリデーションエラーとなったレコードは、エラー理由（エラー内容のサマリー）を添えて `DLQ` リストへ隔離し、後から監査できるようにしなさい。

---

### 📥 入力データの仕様

入力は、LLMが出力した生の文字列のリストです。

```python
raw_llm_outputs = [
    # 1. 完全なJSON
    '{"transaction_id": "tx_101", "user_id": "usr_999", "amount": 1500.0, "currency": "JPY", "timestamp": "2026-06-25T15:00:00Z"}',
    
    # 2. マークダウンで囲まれている
    '```json\n{"transaction_id": "tx_102", "user_id": "usr_888", "amount": 2500.5, "currency": "USD", "timestamp": "2026-06-25T15:01:00Z"}\n```',
    
    # 3. 前後に不要な解説テキストがある
    'Here is the extracted transaction: {"transaction_id": "tx_103", "user_id": "usr_777", "amount": 300, "currency": "EUR", "timestamp": "2026-06-25T15:02:00Z"} hope this helps!',
    
    # 4. 末尾の閉じ括弧が欠けている（かつ通貨が小文字）
    '{"transaction_id": "tx_104", "user_id": "usr_666", "amount": 120.0, "currency": "gbp", "timestamp": "2026-06-25T15:03:00Z"',
    
    # 5. 通貨が小文字（自動大文字変換で救済可能）
    '{"transaction_id": "tx_105", "user_id": "usr_555", "amount": "99.9", "currency": "eur", "timestamp": "2026-06-25T15:04:00Z"}',
    
    # 6. 金額がマイナス（Pydanticバリデーションエラー -> DLQ）
    '{"transaction_id": "tx_106", "user_id": "usr_444", "amount": -10.0, "currency": "JPY", "timestamp": "2026-06-25T15:05:00Z"}',
    
    # 7. user_idが命名規則違反（Pydanticバリデーションエラー -> DLQ）
    '{"transaction_id": "tx_107", "user_id": "guest_user", "amount": 450.0, "currency": "USD", "timestamp": "2026-06-25T15:06:00Z"}',
    
    # 8. 完全に壊れたテキスト（修復不能 -> DLQ）
    'I apologize, but I could not find any transaction details in the provided document.'
]
```

---

### 📤 期待される出力のイメージ

```text
2026-06-25 22:30:00 - INFO - Starting LLM ingestion pipeline...
2026-06-25 22:30:00 - INFO - Processed 8 records.
2026-06-25 22:30:00 - INFO - --- Successfully Ingested (5 records) ---
- TX: tx_101, User: usr_999, Amount: 1500.0 JPY, Time: 2026-06-25 15:00:00+00:00
- TX: tx_102, User: usr_888, Amount: 2500.5 USD, Time: 2026-06-25 15:01:00+00:00
- TX: tx_103, User: usr_777, Amount: 300.0 EUR, Time: 2026-06-25 15:02:00+00:00
- TX: tx_104, User: usr_666, Amount: 120.0 GBP, Time: 2026-06-25 15:03:00+00:00  <- (修復&大文字正規化成功！)
- TX: tx_105, User: usr_555, Amount: 99.9 EUR, Time: 2026-06-25 15:04:00+00:00   <- (文字列からfloatへのキャスト＆大文字変換成功！)

2026-06-25 22:30:00 - INFO - --- Dead Letter Queue (3 records) ---
- Record 5 (Index 5) Failed: Validation Error: Input should be greater than 0 [type=greater_than, input_value=-10.0, ...]
- Record 6 (Index 6) Failed: Validation Error: Value error, user_id must match pattern 'usr_\d+' [type=value_error, ...]
- Record 7 (Index 7) Failed: JSON Decode Error: No JSON object could be decoded from the string.
```

---

### 💡 この課題で学べること（シニアFDEの必須スキル）

- **LLM出力の非決定的動作に対する防御的設計**: LLMは指示（System Prompt）を無視してフォーマットを崩すため、パーサー側で修復可能（Healable）なエラーと修復不能（Unhealable）なエラーを区別する能力。
- **Pydantic v2による宣言的バリデーション**: コードをシンプルに保ちつつ、厳密な型定義とドメインルール（カスタムバリデータ）を適用する技術。
- **DLQパターン**: データレイク/データ基盤において、異常値があっても全体のストリームを止めず、不正データだけを別のパスに切り出す運用のベストプラクティス。

---

## 🛠️ チャレンジ

この堅牢なインジェクション処理を実装するためのテンプレートコードを [main.py](file:///Users/miwanoshuuhei/01_gitProject/09_portfolio/課題16/main.py) に配置したわ。
FDEとして、LLMの気まぐれに負けない「最強のデータ防波堤」を築いてみせなさい！
