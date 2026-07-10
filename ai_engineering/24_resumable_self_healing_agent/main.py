import asyncio
import logging
import re
import json
from openai import AsyncOpenAI
from typing import Any
"""システムの流れ"""
# ユーザが質問する
# ===ループ1開始===
# 質問に対して、LLMを叩く
# LLMが回答を生成する。
# LLMの回答をAgent履歴として保存する
# LLMの回答をパースし、Toolの利用意思がある場合、Toolを実行する。「LLMが最終回答。」として出力してきた場合は、終了する
# Toolの結果をAgent履歴として保存する
# ===ループ2開始===
# 過去のAgent履歴を全てLLMに渡して叩く。以降はループ１と同じ

# ===チェックポイントの復元===
# プロセスがクラッシュした時に備える
# 各ループ内でチェックポイント（Agent履歴）をjsonで取得する
# クラッシュの場合、↑を利用し、状態をリカバリして再開する



# ==========
# logging
# ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==========
# client
# ==========
client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# ==========
# LLMへのリクエスト
# ==========
async def call_llm(history: list[str]) -> str:
    system_prompt = (
        "あなたはタスクを解決するために外部ツールを利用できるAgentです。 \n"
        "利用可能なツールは以下2つです。 \n"
        "get_uinfo(username: str) -> int: \n"
        " - データベースからユーザの年齢を取得するツール。 注意：usernameはstr型で渡すこと\n"
        "caluculate(op: str, val1: int, val2: int) -> int: \n"
        "四則演算を行うツール。opは(+, -, *, /)のいずれか \n"
        "【出力フォーマット】 \n"
        "- Toolを実行する場合"
        "THOUGHT: <現在の思考プロセス> \n"
        "CALL: <ツール名>, ARGS: {\"引数名\": \"値\"} \n\n"
        "例) \n"
        "THOUGHT: アリスの年齢を取得する \n"
        "CALL: get_uinfo, ARGS: {\"username\": \"Alice\"} \n\n"
        "- 最終回答を出力する場合"
        "THOUGHT: <現在の思考プロセス> \n"
        "最終回答: 回答内容 \n\n"
        "【デモンストレーション用の特別ルール】 \n\n"
        "今回の検証ではAgentによる自己修復(self-correction)を確認するために、最初のステップ（Roud0）では、\n"
        "わざと、get_uinfo(username: str)の引数に数値の'123'を渡してください。\n"
        "その後、TypeErrorが発生することを確認し、次のステップで文字列の `\"Alice\"` に修正して再実行（自己修復）してください。\n"
        "この自己修復のデモンストレーション手順を必ず実行すること。"
    )

    formatted_prompt = [{"role": "user", "content": system_prompt}]

    for his in history:
        role = his.get("role")
        content = his.get("content")
        # もしroleがtoolなら補正
        if role == "tool":
            formatted_prompt.append({"role": "user", "content": content})
        else:
            formatted_prompt.append({"role": role, "content": content})

    try:
        response = await client.chat.completions.create(
            model="qwen2.5:3b",
            messages=formatted_prompt,
            temperature=0.0
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"ollamaからの応答が得られませんでした。原因:{e}")
        return f"THOUGHT: エラーが発生しました。\n最終回答: エラーのために処理を中断します "

# ==========
# Tool1
# ==========
def get_uinfo(username: str) -> int:
    if not isinstance(username, str):
        raise TypeError(f"ussernameがstr型ではありません, usernameは{type(username).__name__}")
    
    db = {"bob": 26, "tanaka": 29, "satou": 30, "alice":35}
    user_key = username.lower()

    if not user_key in db:
        raise ValueError(f"{username}はdatabaseに存在しません。")
    
    uname = db.get(user_key)
    return uname
# ==========
# Tool2
# ==========
def caluculate(op: str, val1: int, val2: int) -> int:
    if op not in ("+", "-", "*", "/"):
        raise ValueError(f"opが想定されていない演算方法です:{op}")
    
    if op == "+":
        return val1 + val2
    elif op == "-":
        return val1 - val2
    elif op == "*":
        return val1 * val2
    elif op == "/":
        return val1 / val2


# ==========
# Agentクラス
# ==========
class ResumeableAgent:
    """
    agentの状態を定義(task, hisotry, step, is_completed, final_answer)
    """
    def __init__(self, max_steps: int):
        self.max_steps = max_steps
        self.current_step = 0
        self.task = None
        self.hisotry = []
        self.is_completed = False
        self.finall_answer = None

    """
    agentの初期化
    """
    def initilize_task(self, task: str) -> None:
        self.current_step = 0
        self.task = task
        self.hisotry = [{"role": "user", "content": task}]
        self.is_completed = False
        self.finall_answer = None
    

    """
    agentの状態を出力する(チェックポイント)
    """
    def checkpoint(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "current_step": self.current_step,
            "history": self.hisotry,
            "is_completed": self.is_completed,
            "final_answer": self.finall_answer
        }

    """
    過去のagentの状態を復元する(リカバリ)
    """
    def recoverry_state(self, state: dict[str, Any]) -> None:
        self.current_step = state["current_step"]
        self.task = state["task"]
        self.hisotry = state["history"]
        self.is_completed = state["is_completed"]
        self.final_answer = state["final_answer"]


    """
    Toolの実行
    """
    def execute_tool(self, func_name: str, args: dict[str, Any]) -> Any:

        try:
            if func_name == "get_uinfo":
                username = args.get("username")
                res1 =  get_uinfo(username)
                return f"Success result is {res1}"

            elif func_name == "calculate":
                op = args.get("op")
                val1 = args.get("val1")
                val2 = args.get("val2")
                res2 = caluculate(op, val1, val2)
                return f"Success result is {res2}"
            else:
                return f"Error: Unkonwn Tool Name:{func_name}"
        except Exception as e:
            return f"Error: {type(e).__name__} -{e}"    

    """
    LLMへのリクエスト
    リクエストのパース、Toolの実行呼び出し
    最終回答の抽出
    """
    async def run_step(self) -> None:
        # LLMへのリクエスト
        res = await call_llm(self.hisotry)
        self.hisotry.append({"role": "assistant", "content": res})

        # responseのパース
        call_match = re.search(r"CALL:\s*([a-zA-Z0-9_]+),\s*ARGS:\s*(\{.*\})", res)
        final_match = re.search(r"最終回答:\s*(.*)",res)

        if call_match:
            func_name = call_match.group(1)
            func_arg = call_match.group(2)
            try:
                args = json.loads(func_arg)
                func_res = self.execute_tool(func_name, args)
            except Exception as e:
                logger.info(f"Tool実行エラー: 実行Tool:{func_name} 引数:{func_arg}, 原因{e}")
                func_res = f"Error: {type(e).__name__} -{e}"    
            self.hisotry.append({"role": "tool", "content": func_res})
            logger.info(f"Step{self.current_step} Tool Call {func_name} -> {func_res}")

        elif final_match:
            self.is_completed = True
            answer = final_match.group(1)
            self.final_answer = answer
            logger.info(f"Step{self.current_step} Final Answer reached {self.final_answer}")
        
        self.current_step += 1


# ==========
# エントリーポイント
# ==========
async def main():
    task = "アリスの年齢の2倍は？"
    agent = ResumeableAgent(max_steps=5)
    agent.initilize_task(task)

    # まず2回動かす
    for _ in range(2):
        await agent.run_step()
    
    print(f"2回動かした会話履歴:{agent.hisotry}")

    # クラッシュに備えてリカバリを取る
    checkpoint = agent.checkpoint()
    # 本番を想定し、pythonオブジェクトから、jsonオブジェクトにしておく
    json_checkpoint = json.dumps(checkpoint)

    # クラッシュ発生
    del agent

    # リカバリを実行
    new_agent = ResumeableAgent(max_steps=5)
    new_agent.recoverry_state(json.loads(json_checkpoint))
    print(f"state復帰：過去のりれき{new_agent.hisotry}")


    # 最終回答を得れるまでループ
    max_step = 5

    while not new_agent.is_completed and new_agent.current_step < max_step:
        await new_agent.run_step()

    print("実行結果")
    print(f"ステータス:{new_agent.is_completed}")
    print(f"最終結果:{new_agent.final_answer}")

if __name__ == '__main__':
    asyncio.run(main())


