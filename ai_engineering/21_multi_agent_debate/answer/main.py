import asyncio
import re
import logging
from collections import Counter
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

# =========
# logging設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DebateSimulator")

# ⭕️ Ollama接続用の非同期クライアント初期化
client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Ollama用のダミーキー
)

# ==========================================
# 本物のローカル LLM API 呼び出し関数
# ==========================================
async def mock_llm_query(agent_id: int, query: str, round_num: int, previous_answers: List[str]) -> str:
    """
    ローカルの Ollama (qwen2.5:3b) を呼び出し、討論用の発言を生成する。
    """
    if round_num == 0:
        # ラウンド 0: 初期回答
        prompt = (
            f"あなたは数学の専門家であるエージェント（Agent {agent_id}）です。\n"
            f"以下の算数問題を解いてください。思考プロセスを詳細に記述した上で、\n"
            f"出力の最後に必ず「最終解答: <数値>」（例：最終解答: 12）という形式で解答を書きなさい。\n\n"
            f"【問題】\n{query}"
        )
    else:
        # ラウンド 1以降: 他者の発言を踏まえた討論
        other_responses_formatted = "\n".join(
            [f"エージェント: {ans}" for ans in previous_answers]
        )
        prompt = (
            f"あなたは討論に参加しているエージェント（Agent {agent_id}）です。\n"
            f"以下の算数問題について、前ラウンドにおける他のエージェントの発言が提示されています。\n\n"
            f"【問題】\n{query}\n\n"
            f"【他のエージェントの前ラウンドの発言】\n{other_responses_formatted}\n\n"
            f"他者の回答や計算ステップを注意深く確認し、もし自分の回答に間違いがあれば修正してください。\n"
            f"再度思考プロセスを記述した上で、出力の最後に必ず「最終解答: <数値>」（例：最終解答: 12）という形式で回答を出力してください。"
        )

    try:
        response = await client.chat.completions.create(
            model="qwen2.5:3b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ollamaからの応答取得に失敗しました (Agent {agent_id}): {e}")
        return f"Agent-{agent_id}: Error 最終解答: 0"


# ==========================================
# エージェント討論シミュレータの実装
# ==========================================
class Agent:
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.history: List[str] = []  # 各ラウンドでの自身の回答履歴

    def get_last_response(self) -> Optional[str]:
        return self.history[-1] if self.history else None


class MultiAgentDebateManager:
    def __init__(self, num_agents: int, num_rounds: int):
        self.num_agents = num_agents
        self.num_rounds = num_rounds
        self.agents = [Agent(i) for i in range(num_agents)]

    def extract_answer(self, response: str) -> Optional[str]:
        """
        エージェントのテキストレスポンスから、正規表現を用いて最終解答（数値）を抽出する。
        """
        patterns = [
            r"最終解答:\s*(-?\d+)",       # 「最終解答: 10」
            r"####\s*(-?\d+)",          # 「#### 10」 (GSM8K標準)
            r"answer is\s*(-?\d+)",     # 「answer is 10」
            r"(-?\d+)\s*$"              # 行末の単一数値
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # フォールバックとして、文章に含まれる最後の数値を調べる
        numbers = re.findall(r"-?\d+", response)
        if numbers:
            return numbers[-1]
            
        return None

    async def run_debate(self, query: str) -> str:
        """
        1つのクエリ（問題）に対し、K個のエージェントが Rラウンド 討論を行うループを実行する。
        討論終了後、多数決で合意形成を行い、最も票数の多かった解答を返す。
        """
        # 各エージェントの討論履歴をリセット
        for agent in self.agents:
            agent.history.clear()

        # ラウンド 0: 初期個別回答の並行生成
        logger.info(f"--- [Round 0: 初期回答生成] ---")
        tasks = [
            mock_llm_query(agent.agent_id, query, 0, [])
            for agent in self.agents
        ]
        responses = await asyncio.gather(*tasks)
        for agent, resp in zip(self.agents, responses):
            agent.history.append(resp)
            logger.info(f"Agent {agent.agent_id} (Round 0) -> Extracted: {self.extract_answer(resp)}")

        # 討論ラウンド (1 ~ R) の実行
        for r in range(1, self.num_rounds + 1):
            logger.info(f"--- [Round {r}: 討論ラウンド] ---")
            round_tasks = []
            
            for agent in self.agents:
                # 自分以外のエージェントの前ラウンドの回答を収集（コンテキスト構築）
                other_responses = [
                    other.get_last_response()
                    for other in self.agents
                    if other.agent_id != agent.agent_id and other.get_last_response() is not None
                ]
                
                # エージェント討論用のプロンプト構築とリクエスト予約
                task = mock_llm_query(agent.agent_id, query, r, other_responses)
                round_tasks.append(task)
            
            # 並行討論実行
            round_responses = await asyncio.gather(*round_tasks)
            for agent, resp in zip(self.agents, round_responses):
                agent.history.append(resp)
                logger.info(f"Agent {agent.agent_id} (Round {r}) -> Extracted: {self.extract_answer(resp)}")

        # 合意形成（Majority Vote）
        final_answers = []
        for agent in self.agents:
            last_resp = agent.get_last_response()
            if last_resp:
                ans = self.extract_answer(last_resp)
                if ans is not None:
                    final_answers.append(ans)

        if not final_answers:
            logger.warning("すべてのエージェントから解答を抽出できませんでした。フォールバック値 0 を返します。")
            return "0"

        # 最も票数の多い解答を抽出
        counter = Counter(final_answers)
        most_common = counter.most_common(1)
        final_consensus = most_common[0][0]
        
        logger.info(f"多数決集計結果: {dict(counter)} -> 最終合意: {final_consensus}")
        return final_consensus


# =========
# main
# =========
async def main():
    # テスト問題セット (GSM8K風)
    # queries = [
    #     "Alice has 3 apples. Bob has 2 times as many apples as Alice. Clara has 4 more apples than Bob. How many apples does Clara have in total?",
    #     "A train leaves Station A travelling at 60 km/h. Another train leaves Station B travelling at 80 km/h. If the distance between stations is 280 km, how many hours until they meet?"
    # ]
    # correct_answers = ["10", "2"]


    # テスト問題セット (GSM8K風 + ひっかけ難問)
    queries = [
        "Alice has 3 apples. Bob has 2 times as many apples as Alice. Clara has 4 more apples than Bob. How many apples does Clara have in total?",
        "A train leaves Station A travelling at 60 km/h. Another train leaves Station B travelling at 80 km/h. If the distance between stations is 280 km, how many hours until they meet?",
        "Calculate the result of: 14 - 3 * (5 - 8) + 12 / (2 * 3 - 4)",
        "A farmer has 120 apples. He sells 40 apples to Bob. Then, he gives half of the remaining apples to Charlie. After that, Charlie eats 5 apples and gives 10 apples back to the farmer. How many apples does the farmer have now?",
        "A snail is at the bottom of a 10-meter deep well. Each day, the snail climbs up 3 meters, but each night it slides down 2 meters. On which day will the snail reach the top of the well?"
    ]
    correct_answers = ["10", "2", "29", "50", "8"]


    logger.info("======= 実験開始: 討論なし (エージェント数=1, ラウンド数=0) =======")
    manager_solo = MultiAgentDebateManager(num_agents=1, num_rounds=0)
    solo_correct = 0
    start_time_solo = time.time()
    for q, ans in zip(queries, correct_answers):
        result = await manager_solo.run_debate(q)
        logger.info(f"結果: 回答={result} (正解: {ans})\n")
        if result == ans:
            solo_correct += 1
    duration_solo = time.time() - start_time_solo

    logger.info("======= 実験開始: 討論あり (エージェント数=3, ラウンド数=2) =======")
    manager_debate = MultiAgentDebateManager(num_agents=3, num_rounds=2)
    debate_correct = 0
    start_time_debate = time.time()
    for q, ans in zip(queries, correct_answers):
        result = await manager_debate.run_debate(q)
        logger.info(f"結果: 回答={result} (正解: {ans})\n")
        if result == ans:
            debate_correct += 1
    duration_debate = time.time() - start_time_debate

    print("\n====================================")
    print("🏁 実験レポート（Metrics Summary）")
    print("====================================")
    print(f"1. 単独エージェント (K=1, R=0):")
    print(f"   - 正解率: {solo_correct / len(queries) * 100:.1f}% ({solo_correct}/{len(queries)})")
    print(f"   - 総実行時間: {duration_solo:.2f} 秒")
    print(f"2. 討論エージェント (K=3, R=2):")
    print(f"   - 正解率: {debate_correct / len(queries) * 100:.1f}% ({debate_correct}/{len(queries)})")
    print(f"   - 総実行時間: {duration_debate:.2f} 秒")
    print("====================================")


if __name__ == "__main__":
    import time
    asyncio.run(main())
