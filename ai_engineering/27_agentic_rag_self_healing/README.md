# 💻 課題27：Agentic RAG with Self-Healing（フレームワーク不使用・スクラッチ実装）

> **【Sakana AI FDE 技術課題 想定問題】**
> 本課題は、Sakana AI Forward Deployed Engineer ポジションの技術課題として出題されうる問題を想定して設計されています。
> 「LangChain/LangGraph等の既存フレームワークを使わずに、実装意図を説明できること」を採点の核心とします。

---

## 📖 背景設定（Background）

あなたはある金融機関のクライアントから以下の依頼を受けました。

> 「社内に蓄積された**金融規制レポート（PDF/テキスト）**に対して、アナリストが自然言語で質問できる社内RAGシステムを作ってほしい。ただし、LLMの回答が**ソース文書に根拠を持たない（ハルシネーション）**と判断された場合は、自動で再検索・再回答を試みる仕組みが必要だ。また、**何度試みても回答の品質が基準を満たさない場合は、その旨をユーザーに明示して処理を停止すること**」

---

## 🎯 課題要件（Requirements）

以下の**4つのコンポーネント**を、`LangChain・LlamaIndex・LangGraph等のRAGフレームワークを一切使わずに**スクラッチで実装**しなさい。
使用を許可するライブラリは `openai`（Ollama互換）、`pydantic`、`numpy`（コサイン類似度計算用）のみとします。

---

### コンポーネント1: ドキュメントの取り込みとベクトルインデックス（Naive RAG Layer）

```
rag_pipeline/
├── ingestion.py    # ドキュメント分割・チャンキング
└── vector_store.py # ベクトル検索（インメモリ）
```

- `ingestion.py`: 与えられたテキストを**固定長チャンク**（`chunk_size`, `chunk_overlap` パラメータ）に分割し、各チャンクに `chunk_id` と `source` メタデータを付与すること
- `vector_store.py`: 各チャンクをLLMの `Embedding API` でベクトル化し、**インメモリのNumPy配列**に格納すること。クエリを受け取り、**コサイン類似度**で上位K件を返す `search(query, top_k)` メソッドを実装すること

---

### コンポーネント2: Pydanticによる回答品質スキーマの定義

```
rag_pipeline/
└── schemas.py      # Pydantic モデル
```

LLMに対して、以下のJSON構造で回答を生成させること。フリーテキストでの回答は**禁止**とし、必ずこのスキーマに準拠させること。

```python
class RAGResponse(BaseModel):
    answer: str = Field(..., description="ユーザーへの最終回答")
    sources: list[str] = Field(..., description="回答の根拠となったchunk_idのリスト（必ず1件以上）")
    confidence: float = Field(..., ge=0.0, le=1.0, description="根拠の確かさへの自己評価スコア（0.0〜1.0）")
    needs_retry: bool = Field(..., description="回答の品質が不十分で再検索が必要と判断した場合はTrue")
```

---

### コンポーネント3: Self-Healing RAGループ（本課題の核心）

```
rag_pipeline/
└── agent.py        # Self-HealingループのOrchestrator
```

以下のフローを実装すること。

```
[ユーザークエリ]
      │
      ▼
[Step 1: 検索] vector_store.search() で関連チャンクを取得
      │
      ▼
[Step 2: 生成] チャンクをコンテキストとしてLLMに渡し、RAGResponseスキーマで回答を生成
      │
      ▼
[Step 3: 検証]
      ├─ RAGResponse のパースに失敗（JSONDecodeError / ValidationError）→ エラー内容をLLMにフィードバックして再生成
      ├─ confidence < threshold（例: 0.7）→ needs_retry=True として再検索クエリを拡張して再試行
      ├─ needs_retry == True → 再試行
      └─ 全条件クリア → 回答を返す
      │
      ▼（最大 max_retries 回試行後）
[Step 4: DLQ / Fallback]
      最大試行回数に達した場合は、回答を生成せず
      「信頼できる回答を生成できませんでした」というFallbackレスポンスを返す
```

---

### コンポーネント4: エントリポイントとデモ実行

```
main.py
```

以下のサンプルドキュメント（架空の金融規制テキスト）をインジェストし、3つのクエリに対してSelf-Healing RAGを動作させること。

**サンプルドキュメント（ハードコード可）:**
```
金融規制レポート第3条: 全ての金融機関は、顧客との取引において、
取引金額が100万円を超える場合、翌営業日中に規制当局へ報告義務を負う。

金融規制レポート第7条: マネーロンダリング防止（AML）の観点から、
同一顧客からの24時間以内の取引合計が500万円を超えた場合、
システムは自動的にフラグを立て、コンプライアンス部門へ通知しなければならない。

金融規制レポート第12条: 外国送金については、送金元・送金先の
金融機関情報および受取人情報を記録し、10年間保管する義務がある。
```

**テストクエリ:**
1. `"100万円を超える取引の報告義務について教えてください"` → 根拠あり、高confidenceで回答できるはず
2. `"AMLフラグが立つ条件は何ですか"` → 根拠あり、高confidenceで回答できるはず
3. `"仮想通貨取引の規制について教えてください"` → **根拠なし**。`needs_retry=True` → 最終的に Fallback になることを確認

---

## 📁 ファイル構成（期待するディレクトリ構造）

```
27_agentic_rag_self_healing/
├── README.md
├── main.py                     # デモ実行エントリポイント（ここを埋めなさい）
└── rag_pipeline/
    ├── __init__.py
    ├── ingestion.py            # ドキュメント分割（ここを埋めなさい）
    ├── vector_store.py         # ベクトル検索（ここを埋めなさい）
    ├── schemas.py              # Pydanticスキーマ（ここを埋めなさい）
    └── agent.py                # Self-Healingオーケストレーター（ここを埋めなさい）
```

---

## 🚫 禁止事項（Must NOT Use）

| 禁止ライブラリ | 理由 |
|:---|:---|
| `langchain` / `langchain_core` | RAGパイプライン全体を隠蔽するため |
| `llama_index` | ドキュメント分割・検索を隠蔽するため |
| `langgraph` | オーケストレーションロジックを隠蔽するため |
| `chromadb` / `faiss` / `pinecone` | ベクトル検索の実装を隠蔽するため |
| `tiktoken` 以外のチャンキングライブラリ | - |

> ⚠️ **なぜフレームワークを禁止するのか？**
> FDEは顧客環境（エアギャップ・Gov-Cloud・特殊なオンプレ環境等）に応じて、「このライブラリが使えない」という制約に直面することがあります。
> スクラッチで実装できる力は、**あらゆる環境への適応力の証明**です。

---

## 📊 採点基準（Evaluation Rubric）

| 項目 | 配点 | 評価ポイント |
|:---|:---:|:---|
| **コンポーネント1: Ingestion & Vector Store** | 20点 | コサイン類似度の実装、メタデータ設計の妥当性 |
| **コンポーネント2: Pydanticスキーマ** | 15点 | `ValidationError` ハンドリングの実装、型安全性 |
| **コンポーネント3: Self-Healingループ** | 40点 | 再試行ロジックの正確性、Fallback処理、無限ループ防止 |
| **コンポーネント4: デモ実行** | 10点 | 3つのクエリに対する期待動作の確認 |
| **設計判断の言語化（コードコメント・README）** | 15点 | 「なぜこの設計か」「代替案は何か」のドキュメント化 |

---

## 💬 提出時に回答すべき設計上の問い（Design Questions）

実装完了後、以下の問いに対して**コードコメントまたはREADMEに追記する形で回答**すること。
これらは面接における口頭試問でも問われることを想定している。

1. **「なぜLangChainではなくスクラッチで実装したのか？その技術選定の根拠を説明せよ」**
2. **「`confidence`スコアはどこで計算されているか？LLMの自己評価は信頼できるか？より客観的な評価方法（例: RAGAS等）と比較した際のトレードオフは何か？**」
3. **「このシステムをプロダクション環境に移行する場合、インメモリのベクトルストアに代わり何を採用するか？Snowflake Cortex / pgvector / Pineconeの中から選んで理由を述べよ」**
4. **「Self-Healingループが `max_retries` 回で終わらず無限に回り続けるバグが起きた場合、それはどこに原因があり、どのコードで防いでいるか説明せよ」**

---

## 🔧 環境セットアップ

```bash
# Ollamaが起動していること（ローカルLLM）
ollama serve
ollama pull qwen2.5:3b  # LLM用
ollama pull nomic-embed-text  # Embedding用

# 依存ライブラリ
pip install openai pydantic numpy
```

`.env` に以下を設定:
```
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_LLM_MODEL=qwen2.5:3b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

---

## 🏁 ゴール（Definition of Done）

```
$ python main.py

✅ Query 1: "100万円を超える取引の報告義務について..."
   → answer: "全ての金融機関は翌営業日中に..."
   → sources: ["chunk_001"]
   → confidence: 0.92
   → retries: 0

✅ Query 2: "AMLフラグが立つ条件は..."
   → answer: "同一顧客の24時間以内の合計が500万円を超えた場合..."
   → sources: ["chunk_002"]
   → confidence: 0.88
   → retries: 0

⚠️  Query 3: "仮想通貨取引の規制について..."
   → [Retry 1] confidence=0.3, needs_retry=True. Expanding query...
   → [Retry 2] confidence=0.2, needs_retry=True. Expanding query...
   → [Retry 3] confidence=0.1, needs_retry=True. Max retries reached.
   → ❌ Fallback: "信頼できる回答をソース文書から生成できませんでした。専門家にお問い合わせください。"
```

---

*このREADMEは Sakana AI FDE 技術課題の「想定問題」として作成されました。*
*実装の正解例は `answer/` ディレクトリに格納されています。*
