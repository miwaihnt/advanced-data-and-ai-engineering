"""
課題27: Agentic RAG with Self-Healing
コンポーネント4: エントリポイント & デモ実行

ここを実装しなさい。
"""
import asyncio
import logging
import os
from openai import AsyncOpenAI

from rag_pipeline import (
    split_document,
    InMemoryVectorStore,
    SelfHealingRAGAgent,
    RAGResponse,
    FallbackResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("Main")

# ============================================================
# サンプルドキュメント（架空の金融規制テキスト）
# ============================================================
SAMPLE_DOCUMENTS = [
    {
        "source": "金融規制レポート.txt",
        "text": """
金融規制レポート第3条: 全ての金融機関は、顧客との取引において、
取引金額が100万円を超える場合、翌営業日中に規制当局へ報告義務を負う。

金融規制レポート第7条: マネーロンダリング防止（AML）の観点から、
同一顧客からの24時間以内の取引合計が500万円を超えた場合、
システムは自動的にフラグを立て、コンプライアンス部門へ通知しなければならない。

金融規制レポート第12条: 外国送金については、送金元・送金先の
金融機関情報および受取人情報を記録し、10年間保管する義務がある。
        """.strip()
    }
]

# ============================================================
# テストクエリ
# クエリ1, 2: ソース文書に根拠あり → 高confidence回答
# クエリ3: ソース文書に根拠なし → Self-Healing後 Fallback
# ============================================================
TEST_QUERIES = [
    "100万円を超える取引の報告義務について教えてください",
    "AMLフラグが立つ条件は何ですか",
    "仮想通貨取引の規制について教えてください",
]


async def main():
    client = AsyncOpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="ollama",
    )
    llm_model = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:3b")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # -------------------------------------------
    # Step 1: ドキュメントのインジェスト
    # -------------------------------------------
    logger.info("📄 Ingesting documents...")

    # TODO: SAMPLE_DOCUMENTSをsplit_document()でチャンク化しなさい
    all_chunks = []
    # for doc in SAMPLE_DOCUMENTS:
    #     chunks = split_document(...)
    #     all_chunks.extend(chunks)

    # -------------------------------------------
    # Step 2: ベクトルストアの構築
    # -------------------------------------------
    logger.info("🔢 Building vector index...")

    # TODO: InMemoryVectorStoreを初期化し、チャンクを追加しなさい
    # vector_store = InMemoryVectorStore(...)
    # await vector_store.add_chunks(all_chunks)

    # -------------------------------------------
    # Step 3: Self-Healing RAG エージェントの初期化
    # -------------------------------------------

    # TODO: SelfHealingRAGAgentを初期化しなさい
    # agent = SelfHealingRAGAgent(...)

    # -------------------------------------------
    # Step 4: テストクエリの実行
    # -------------------------------------------
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"🔍 Query {i}: {query}")
        print('='*60)

        # TODO: agent.query(query) を呼び出して結果を表示しなさい
        # result = await agent.query(query)

        # if isinstance(result, RAGResponse):
        #     print(f"✅ Answer   : {result.answer}")
        #     print(f"   Sources  : {result.sources}")
        #     print(f"   Confidence: {result.confidence:.2f}")
        # elif isinstance(result, FallbackResponse):
        #     print(f"❌ Fallback : {result.message}")
        #     print(f"   Retries  : {result.total_retries}")
        pass


if __name__ == "__main__":
    asyncio.run(main())
