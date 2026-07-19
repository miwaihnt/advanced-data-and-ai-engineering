"""
課題28: 自律テスト・修復マルチエージェント
コンポーネント3: Orchestrator（協調ループの管理）

ここを実装しなさい。
"""
import logging
from .agents import CoderAgent, ReviewerAgent, TesterAgent
from .schemas import ScientistReport

logger = logging.getLogger("Orchestrator")


class ScientistOrchestrator:
    """
    Coder, Reviewer, Testerを協調させて
    「修正→レビュー→テスト→再修正」のループを管理するクラス。
    """
    def __init__(
        self,
        coder: CoderAgent,
        reviewer: ReviewerAgent,
        tester: TesterAgent,
        max_iterations: int = 5
    ):
        self.coder = coder
        self.reviewer = reviewer
        self.tester = tester
        self.max_iterations = max_iterations
        self.history: list[str] = []

    async def run(self, original_code: str, test_code: str) -> ScientistReport:
        """
        TODO: 自律修復の協調ループを実装しなさい。
        
        フロー:
        1. Coderが修正案を作成 (generate_fix)
        2. Reviewerが修正案をレビュー (review)
           - もしリジェクトされたら、レビューフィードバックをhistoryに追加して1に戻る
        3. 合格したら、Testerがテストを実行 (run_tests)
           - もしテストがすべてパスしたら、ループを抜けて正常終了レポートを返す
           - もしテストが失敗したら、エラーログをhistoryに追加して1に戻る
        4. max_iterations に達してもパスしなかったら、失敗レポートを返す
        """
        self.history = []

        last_fixed_code = original_code
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"🔄 Starting Iteration {iteration}/{self.max_iterations}...")

            # 1. Coderが修正案を作成
            try:
                modification = await self.coder.generate_fix(original_code, test_code, self.history)
                logger.info(f"🧑‍💻 Coder proposed a fix. Explanation: {modification.explanation}")
            except Exception as e:
                err_msg = f"Coder generation failed at iteration {iteration}: {str(e)}"
                logger.error(err_msg)
                self.history.append(err_msg)
                continue

            last_fixed_code = modification.fixed_code

            # 2. Reviewerが修正案をレビュー
            try:
                review_result = await self.reviewer.review(original_code, modification.fixed_code, modification.explanation)
                logger.info(f"🕵️ Reviewer feedback: Approved={review_result.approved}. Feedback: {review_result.feedback}")
            except Exception as e:
                err_msg = f"Reviewer validation failed at iteration {iteration}: {str(e)}"
                logger.error(err_msg)
                self.history.append(err_msg)
                continue

            if not review_result.approved:
                reject_msg = f"[Iteration {iteration} Review Reject] {review_result.feedback}"
                self.history.append(reject_msg)
                continue

            # 3. 合格したら、Testerがテストを実行
            logger.info(f"🧪 Running tests for iteration {iteration}...")
            test_success, test_output = self.tester.run_tests(modification.fixed_code)

            if test_success:
                logger.info(f"🎉 Test passed at iteration {iteration}!")
                self.history.append(f"[Iteration {iteration} Test Success] {test_output}")
                return ScientistReport(
                    success=True,
                    total_iterations=iteration,
                    final_code=modification.fixed_code,
                    modification_history=self.history
                )
            else:
                fail_msg = f"[Iteration {iteration} Test Fail] {test_output}"
                logger.warning(f"❌ Test failed at iteration {iteration}.")
                self.history.append(fail_msg)

        logger.error(f"🚨 Failed to fix the code within {self.max_iterations} iterations.")
        return ScientistReport(
            success=False,
            total_iterations=self.max_iterations,
            final_code=last_fixed_code,
            modification_history=self.history
        )
