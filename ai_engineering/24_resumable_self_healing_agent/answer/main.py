import re
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI

# =========
# logging設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResumableAgent")

# ⭕️ Ollama接続用の非同期クライアント初期化
client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)


# ==========================================
# Tools (エージェントが呼び出す外部関数)
# ==========================================
def fetch_user_age(username: str) -> int:
    """データベースからユーザーの年齢を取得するツール"""
    # 厳格な引数検証
    if not isinstance(username, str):
        raise TypeError(f"username must be a string, got {type(username).__name__}")
        
    db = {"alice": 28, "bob": 34, "clara": 40}
    user_key = username.lower()
    if user_key not in db:
        raise ValueError(f"User '{username}' not found in database.")
    return db[user_key]


def calculate(op: str, val1: float, val2: float) -> float:
    """計算機ツール (op: '+', '-', '*', '/')"""
    if op not in ["+", "-", "*", "/"]:
        raise ValueError(f"Unsupported operator: {op}")
    if op == "/" and val2 == 0:
        raise ZeroDivisionError("Division by zero is not allowed.")
    
    if op == "+": return val1 + val2
    if op == "-": return val1 - val2
    if op == "*": return val1 * val2
    if op == "/": return val1 / val2


# ==========================================
# 本物のローカル LLM API 呼び出し関数 (Ollama版)
# ==========================================
async def query_ollama_agent(history: List[Dict[str, Any]]) -> str:
    """
    ローカルの Ollama (qwen2.5:3b) を呼び出し、エージェントの次の思考・行動を生成する。
    """
    system_prompt = (
        "あなたはタスクを解決するために外部ツールを利用できる自律型エージェントです。\n"
        "利用可能なツールは以下の2つです：\n"
        "1. fetch_user_age(username: str) -> int\n"
        "   - データベースからユーザーの年齢を取得するツール。※注意: usernameは必ず文字列で指定すること。\n"
        "2. calculate(op: str, val1: float, val2: float) -> float\n"
        "   - 四則演算を行う計算機ツール。(op は '+', '-', '*', '/' のいずれか)\n\n"
        "【出力フォーマット】\n"
        "毎ターン、必ず以下のいずれかのフォーマットで出力してください。余計な挨拶や説明は一切出力しないでください。\n\n"
        "■ ツールを実行する場合:\n"
        "THOUGHT: <現在の思考プロセス>\n"
        "CALL: <ツール名>, ARGS: {\"<引数名>\": <値>}\n"
        "例:\n"
        "THOUGHT: アリスの年齢を取得する。\n"
        "CALL: fetch_user_age, ARGS: {\"username\": \"alice\"}\n\n"
        "■ 最終回答を出力する場合:\n"
        "THOUGHT: <現在の思考プロセス>\n"
        "最終回答: <回答の内容>\n\n"
        "【デモンストレーション用の特別ルール（重要）】\n"
        "今回の実行では『自己修復（Self-Correction）』の機能を確認するため、最初のステップ（Round 0）では、\n"
        "わざと `fetch_user_age` の username 引数に数値の `123` を渡してください。\n"
        "その後、TypeErrorが発生することを確認し、次のステップで文字列の `\"Alice\"` に修正して再実行（自己修復）してください。\n"
        "この自己修復のデモンストレーション手順を必ず実行すること。"
    )

    # API互換性のためにメッセージリストを整形
    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        if role == "tool":
            # toolロールはOpenAI/Ollama APIのチャット履歴でエラーになりやすいため、user発言としてラップ
            formatted_messages.append({"role": "user", "content": f"【ツール実行結果】: {content}"})
        else:
            formatted_messages.append({"role": role, "content": content})

    try:
        response = await client.chat.completions.create(
            model="qwen2.5:3b",
            messages=formatted_messages,
            temperature=0.0  # 思考のブレを防ぐために決定論的にする
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ollamaからの思考取得に失敗しました: {e}")
        return "THOUGHT: エラーが発生しました。\n最終回答: エラーのため処理を中断します。"


# ==========================================
# 状態シリアライズ・自己修復付きエージェントの実装
# ==========================================
class ResumableAgent:
    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps
        self.task: str = ""
        self.current_step: int = 0
        self.history: List[Dict[str, Any]] = []
        self.is_completed: bool = False
        self.final_answer: Optional[str] = None

    def initialize_task(self, task: str) -> None:
        """
        新しいタスクをセットし、履歴を初期化する。
        """
        self.task = task
        self.current_step = 0
        self.history = [{"role": "user", "content": task}]
        self.is_completed = False
        self.final_answer = None

    def checkpoint(self) -> Dict[str, Any]:
        """
        エージェントの現在のステータスを辞書形式で出力（シリアライズ）する。
        """
        return {
            "task": self.task,
            "current_step": self.current_step,
            "history": self.history,
            "is_completed": self.is_completed,
            "final_answer": self.final_answer
        }

    def load_checkpoint(self, state: Dict[str, Any]) -> None:
        """
        渡された辞書オブジェクト（シリアライズデータ）から、エージェントの状態を復元する。
        """
        self.task = state["task"]
        self.current_step = state["current_step"]
        self.history = state["history"]
        self.is_completed = state["is_completed"]
        self.final_answer = state["final_answer"]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """
        name に対応する関数（fetch_user_age または calculate）を実行し、結果を文字列で返す。
        例外が発生した場合は、エラーメッセージを返す。
        """
        try:
            if name == "fetch_user_age":
                username = args.get("username")
                age = fetch_user_age(username)
                return f"Success: User age is {age}"
                
            elif name == "calculate":
                op = args.get("op")
                val1 = float(args.get("val1", 0))
                val2 = float(args.get("val2", 0))
                res = calculate(op, val1, val2)
                return f"Success: Calculation result is {res}"
                
            else:
                return f"Error: Unknown tool name '{name}'"
                
        except Exception as e:
            # 例外クラス名とエラー内容を文字列表現でキャッチして返す（自己修復に再供給するため）
            return f"Error: {type(e).__name__} - {e}"

    async def run_step(self) -> None:
        """
        エージェントの思考・実行ループを「1ステップ分」だけ進める（非同期化）。
        """
        if self.is_completed:
            return

        # 1. LLMによる次の思考・判断の取得
        llm_response = await query_ollama_agent(self.history)
        
        # 履歴への追加
        self.history.append({"role": "assistant", "content": llm_response})

        # 2. パース処理
        # CALL: <ツール名>, ARGS: <JSON> のマッチング
        call_match = re.search(r"CALL:\s*([a-zA-Z0-9_]+),\s*ARGS:\s*(\{.*\})", llm_response)
        # 最終回答: <内容> のマッチング
        final_match = re.search(r"最終回答:\s*(.*)", llm_response)

        if call_match:
            tool_name = call_match.group(1)
            args_json = call_match.group(2)
            
            try:
                tool_args = json.loads(args_json)
                # ツールの実行とエラーの自動捕捉
                tool_result = self.execute_tool(tool_name, tool_args)
            except json.JSONDecodeError as je:
                tool_result = f"Error: JSONDecodeError - Invalid JSON arguments: {je}"
            except Exception as e:
                tool_result = f"Error: {type(e).__name__} - {e}"
            
            # ツール実行結果（成功 or エラー）を履歴へ保存して次の思考にフィードバック
            self.history.append({"role": "tool", "content": tool_result})
            logger.info(f"[Step {self.current_step}] Tool Call: {tool_name}({args_json}) -> {tool_result}")

        elif final_match:
            self.is_completed = True
            self.final_answer = final_match.group(1).strip()
            logger.info(f"[Step {self.current_step}] Final Answer reached: {self.final_answer}")

        self.current_step += 1


# =========
# main
# =========
async def main():
    task = "Aliceの年齢の2倍はいくつか教えて。"
    
    print("--- 🚀 フェーズ 1: エージェントの起動と途中クラッシュのシミュレーション ---")
    agent = ResumableAgent(max_steps=5)
    agent.initialize_task(task)
    
    # 2ステップだけ実行する（ここで型エラー ➔ 自己修復で正しい年齢取得まで進む）
    for _ in range(2):
        await agent.run_step()
        
    print(f"現在のステップ数: {agent.current_step}")
    print(f"ここまでの履歴数: {len(agent.history)}")
    
    # 状態のチェックポイント保存 (JSONシリアライズを模倣)
    state_json = json.dumps(agent.checkpoint())
    print("\n--- 💾 チェックポイント保存データ (JSON) ---")
    print(state_json)
    
    print("\n--- 💥 クラッシュシミュレーション (プロセス再起動) ---")
    del agent  # メモリから消去してプロセス終了をシミュレート
    
    print("\n--- 🔄 フェーズ 2: 状態をロードして続きから実行 ---")
    restored_state = json.loads(state_json)
    
    new_agent = ResumableAgent(max_steps=5)
    new_agent.load_checkpoint(restored_state)
    
    # 続きから実行する
    step_limit = 5
    while not new_agent.is_completed and new_agent.current_step < step_limit:
        logger.info(f"ステップ {new_agent.current_step + 1} を再開実行中...")
        await new_agent.run_step()
        
    print("\n--- 🏁 実行結果 ---")
    print(f"完了ステータス: {new_agent.is_completed}")
    print(f"最終解答: {new_agent.final_answer}")


if __name__ == "__main__":
    asyncio.run(main())
