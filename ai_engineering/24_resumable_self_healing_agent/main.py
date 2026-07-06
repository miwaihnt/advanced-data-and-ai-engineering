import json
import logging
from typing import Any, Dict, List, Optional, Tuple

# =========
# logging設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResumableAgent")


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
# Mock LLM API (エージェントの思考シミュレーション)
# ==========================================
def mock_agent_llm(history: List[Dict[str, Any]]) -> str:
    """
    自己修復のループと状態保存を確認するために、以下のストーリーに沿って
    決まったツールコールと結果を返す模擬エージェントLLM。
    
    ストーリー:
    1. 最初: Aliceの年齢を取得するため、意図的に型エラーを起こす `fetch_user_age(123)` を呼ぶ。
    2. エラーフィードバック後: エラーを検知して自己修復し、正しく `fetch_user_age("Alice")` を呼ぶ。
    3. 年齢(=28)取得後: 年齢に 2 を掛け算するため、`calculate("*", 28, 2)` を呼ぶ。
    4. 計算結果(=56)取得後: 最終回答「Aliceの年齢の2倍は56歳です」を出力する。
    """
    step = len([msg for msg in history if msg.get("role") == "assistant"])

    if step == 0:
        return (
            "THOUGHT: Aliceの年齢の2倍を求めたい。まずは年齢をデータベースから取得する。\n"
            "CALL: fetch_user_age, ARGS: {\"username\": 123}" # 👈 意図的な型エラー(数字)
        )
    
    elif step == 1:
        # 直前のツール実行でエラーが起きているか確認
        last_msg = history[-1]
        if last_msg.get("role") == "tool" and "TypeError" in last_msg.get("content", ""):
            return (
                "THOUGHT: おっと、username引数に数値を渡してしまったのでTypeErrorが起きたわ。次は文字列でリトライする。\n"
                "CALL: fetch_user_age, ARGS: {\"username\": \"Alice\"}" # 👈 自己修復
            )
        return "THOUGHT: エラーが検知できませんでした。 最終回答: エラー"

    elif step == 2:
        return (
            "THOUGHT: 年齢は28歳と分かった。次はこれを2倍にするために計算ツールを呼び出す。\n"
            "CALL: calculate, ARGS: {\"op\": \"*\", \"val1\": 28, \"val2\": 2}"
        )
        
    else:
        return (
            "THOUGHT: すべての計算が完了した。最終解答をユーザーに返す。\n"
            "最終回答: Aliceの年齢の2倍は56歳です。"
        )


# ==========================================
# 【課題】状態シリアライズ・自己修復付きエージェントの実装
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
        # TODO: 状態シリアライズの辞書オブジェクトを構築して返しなさい。
        pass

    def load_checkpoint(self, state: Dict[str, Any]) -> None:
        """
        渡された辞書オブジェクト（シリアライズデータ）から、エージェントの状態を復元する。
        """
        # TODO: 状態復元処理を実装しなさい。
        pass

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """
        name に対応する関数（fetch_user_age または calculate）を実行し、結果を文字列で返す。
        引数の例外（TypeError, ValueError, ZeroDivisionError）が発生した場合は、
        例外を上に投げず、例外のクラス名とメッセージを含んだ文字列を返しなさい（自己修復用）。
        """
        # TODO: 関数の安全な呼び出しと、例外トラップ＆文字列化処理を実装しなさい。
        pass

    def run_step(self) -> None:
        """
        エージェントの思考・実行ループを「1ステップ分」だけ進める。
        
        【処理の流れ】
        1. `mock_agent_llm(self.history)` を呼び出してLLMの判断を取得する。
        2. LLMの出力から「THOUGHT:」や「CALL:」、「最終回答:」をパースする。
        3. 「CALL: <関数名>, ARGS: <JSON引数>」が含まれている場合:
           - ツールを実行し、その結果（またはエラー情報）を `role: tool` のメッセージとして history に追加する。
        4. 「最終回答: <内容>」が含まれている場合:
           - 完了フラグをセットし、`final_answer` に結果を格納する。
        5. `current_step` を 1 インクリメントする。
        """
        # TODO: 1ステップ実行用のロジックを実装しなさい。
        # ヒント: LLMの出力は "CALL: fetch_user_age, ARGS: {\"username\": 123}" のような形式です。
        # 正規表現や文字列スライスを用いてパースしなさい。
        pass


# =========
# main
# =========
def main():
    task = "Aliceの年齢の2倍はいくつか教えて。"
    
    print("--- 🚀 フェーズ 1: エージェントの起動と途中クラッシュのシミュレーション ---")
    agent = ResumableAgent(max_steps=5)
    agent.initialize_task(task)
    
    # 2ステップだけ実行する（ここで型エラー ➔ 自己修復で正しい年齢取得まで進む）
    for _ in range(2):
        agent.run_step()
        
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
        new_agent.run_step()
        
    print("\n--- 🏁 実行結果 ---")
    print(f"完了ステータス: {new_agent.is_completed}")
    print(f"最終解答: {new_agent.final_answer}")


if __name__ == "__main__":
    main()
