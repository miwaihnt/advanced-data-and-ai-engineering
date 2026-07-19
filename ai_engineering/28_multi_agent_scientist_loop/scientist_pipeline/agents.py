"""
課題28: 自律テスト・修復マルチエージェント
コンポーネント2: 各種エージェントのインターフェース設計

ここを実装しなさい。
"""
import json
import re
import subprocess
from openai import AsyncOpenAI
from .schemas import CodeModification, ReviewResult


def _parse_json(text: str) -> dict:
    """LLMのレスポンスからJSON部分を取り出してパースする"""
    text = text.strip()
    
    # 1. まずコードブロックから抽出を試みる
    match_code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match_code_block:
        text = match_code_block.group(1).strip()
    else:
        # 2. コードブロックがない場合、最初の { から 最後の } を抽出
        match_json_braces = re.search(r"(\{[\s\S]*\})", text)
        if match_json_braces:
            text = match_json_braces.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            msg=f"{e.msg} (Failed to parse JSON. Raw text: {repr(text)})",
            doc=e.doc,
            pos=e.pos
        )


class CoderAgent:
    """
    エラーログやレビュー指摘を反映させ、target_code.py を書き換えるエージェント。
    """
    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    async def generate_fix(
        self,
        original_code: str,
        test_code: str,
        feedback_history: list[str]
    ) -> CodeModification:
        """
        元のコード、テストコード、そして履歴（エラーログやレビューの指摘）を
        LLMに渡して、修正版のコードを CodeModification スキーマに従って生成させなさい。
        """
        history_str = "\n".join([f"- {item}" for item in feedback_history]) if feedback_history else "No previous attempts."

        system_prompt = (
            "You are an expert Python developer tasked with fixing bugs in a program. "
            "You must modify the program so that all tests pass. "
            "You MUST return your response in JSON format matching the schema:\n"
            "{\n"
            '  "explanation": "Brief description of the fix",\n'
            '  "fixed_code": "The complete modified Python code"\n'
            "}\n"
            "CRITICAL: Since the response must be a valid JSON object, you MUST properly escape all special characters "
            "inside the JSON string values. Especially, escape all newlines as '\\n' and all double quotes as '\\\"' inside 'fixed_code'. "
            "Do not output raw newlines or unescaped quotes inside the JSON string fields. "
            "Only return the raw JSON object."
        )

        user_prompt = (
            f"### Original Program (target_code.py):\n"
            f"```python\n{original_code}\n```\n\n"
            f"### Test Cases (test_target_code.py):\n"
            f"```python\n{test_code}\n```\n\n"
            f"### Previous Feedback & Errors:\n"
            f"{history_str}\n\n"
            f"Please output a JSON response containing the explanation and the full fixed_code."
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        content = response.choices[0].message.content or ""
        parsed = _parse_json(content)
        return CodeModification.model_validate(parsed)


class ReviewerAgent:
    """
    Coderの書いたコードを静的に検証（レビュー）するエージェント。
    """
    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    async def review(
        self,
        original_code: str,
        fixed_code: str,
        explanation: str
    ) -> ReviewResult:
        """
        修正コードと解説を読み込み、レビュー結果を ReviewResult スキーマに従って
        生成させなさい。
        """
        system_prompt = (
            "You are a strict, professional Python Code Reviewer.\n"
            "Your job is to review a proposed bug fix and ensure that:\n"
            "1. The fix logically addresses the requirements (fixing VIP discounts, string pricing casts, case-insensitivity).\n"
            "2. The fix does NOT contain hallucinations, unnecessary imports, or regressions.\n"
            "3. The fix does NOT attempt to bypass constraints or rewrite/disable the tests themselves (which would be cheating).\n"
            "4. The original program structure is preserved, and the code is high quality.\n\n"
            "You MUST return your response in JSON format matching the schema:\n"
            "{\n"
            '  "approved": true/false,\n'
            '  "feedback": "Detailed feedback explanation. If rejected, list specific issues to fix. If approved, state why."\n'
            "}\n"
            "Only return the JSON object."
        )

        user_prompt = (
            f"### Original Program:\n"
            f"```python\n{original_code}\n```\n\n"
            f"### Proposed Fix:\n"
            f"```python\n{fixed_code}\n```\n\n"
            f"### Coder's Explanation:\n"
            f"{explanation}\n\n"
            f"Review the code and output the JSON response containing approved and feedback."
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        content = response.choices[0].message.content or ""
        parsed = _parse_json(content)
        return ReviewResult.model_validate(parsed)


class TesterAgent:
    """
    修正されたコードを実際にテスト実行する環境エージェント（LLMは使用しない）。
    """
    def __init__(self, target_filepath: str, test_filepath: str):
        self.target_filepath = target_filepath
        self.test_filepath = test_filepath

    def run_tests(self, fixed_code: str) -> tuple[bool, str]:
        """
        修正コードを実際に target_filepath に書き出し、
        subprocess で pytest を実行しなさい。
        
        Returns:
            (Success: bool, Output: str)
            成功時は (True, "All tests passed!")、
            失敗時は (False, pytestの実行ログ/スタックトレース) を返すこと。
        """
        # target_filepath に fixed_code を書き込む
        with open(self.target_filepath, "w", encoding="utf-8") as f:
            f.write(fixed_code)

        try:
            # pytest を実行。pytest がローカル環境にある前提
            # pytest の代わりに python -m pytest でも動くように呼び出し
            result = subprocess.run(
                ["pytest", self.test_filepath],
                capture_output=True,
                text=True,
                timeout=30
            )
            success = (result.returncode == 0)
            output = result.stdout + "\n" + result.stderr
            if success:
                return True, "All tests passed!"
            else:
                return False, output.strip()
        except FileNotFoundError:
            # pytest コマンドが見つからない場合、python -m pytest を試す
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", self.test_filepath],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                success = (result.returncode == 0)
                output = result.stdout + "\n" + result.stderr
                if success:
                    return True, "All tests passed!"
                else:
                    return False, output.strip()
            except Exception as e:
                return False, f"Failed to execute tests due to missing testing tool/environment: {str(e)}"
        except Exception as e:
            return False, f"An unexpected error occurred during test execution: {str(e)}"

