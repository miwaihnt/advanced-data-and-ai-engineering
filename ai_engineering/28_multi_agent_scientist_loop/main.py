"""
課題28: 自律テスト・修復マルチエージェント
コンポーネント4: エントリポイント (main.py)

ここを実装しなさい。
"""
import asyncio
import logging
import os
from openai import AsyncOpenAI

from scientist_pipeline import (
    CoderAgent,
    ReviewerAgent,
    TesterAgent,
    ScientistOrchestrator,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("Main")


async def main():
    client = AsyncOpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="ollama",
    )
    model_name = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:3b")

    # パス設定
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_filepath = os.path.join(base_dir, "target_code.py")
    test_filepath = os.path.join(base_dir, "test_target_code.py")

    # ファイルの読み込み
    with open(target_filepath, "r", encoding="utf-8") as f:
        original_code = f.read()

    with open(test_filepath, "r", encoding="utf-8") as f:
        test_code = f.read()

    logger.info("🧪 Initializing Multi-Agent Scientist System...")

    # 1. 各エージェント（Coder, Reviewer, Tester）のインスタンスを作成しなさい
    coder = CoderAgent(client, model_name)
    reviewer = ReviewerAgent(client, model_name)
    tester = TesterAgent(target_filepath, test_filepath)

    # 2. Orchestratorのインスタンスを作成しなさい
    orchestrator = ScientistOrchestrator(coder, reviewer, tester, max_iterations=5)

    # 3. ループを実行しなさい
    logger.info("🚀 Starting Autonomous Repair Loop...")
    
    # 動的書き換えのためのバックアップを退避
    backup_content = original_code

    try:
        report = await orchestrator.run(original_code, test_code)

        # 4. レポート結果を表示しなさい
        print("\n" + "="*80)
        print("📊 FINAL SCIENTIST REPORT")
        print("="*80)
        print(f"Success         : {report.success}")
        print(f"Total Iterations: {report.total_iterations}")
        print("\n--- Modification History ---")
        for h in report.modification_history:
            print(f" - {h}")
        print("\n--- Final Fixed Code ---")
        print(report.final_code)
        print("="*80)
    finally:
        # target_code.pyを元の状態に復元
        with open(target_filepath, "w", encoding="utf-8") as f:
            f.write(backup_content)
        logger.info("♻️ Restored the original target_code.py from backup.")


if __name__ == "__main__":
    asyncio.run(main())
