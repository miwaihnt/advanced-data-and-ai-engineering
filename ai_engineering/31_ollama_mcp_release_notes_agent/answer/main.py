"""Main execution script for Ollama + GitHub MCP + FastMCP Release Notes Agent.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add current answer directory to path
sys.path.append(str(Path(__file__).parent))

from mcp_client import MultiMCPClient


async def main():
    print("=" * 60)
    print("🚀 Initializing Multi-Server MCP Agent (Ollama + GitHub MCP + FastMCP)")
    print("=" * 60)

    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    client = MultiMCPClient(ollama_model=model_name)

    answer_dir = Path(__file__).parent
    python_exec = sys.executable

    # 1. Connect to Custom FastMCP Server
    print("Connecting to Custom FastMCP Server...")
    await client.connect_to_server(
        name="release_notes_server",
        command=python_exec,
        args=[str(answer_dir / "custom_mcp_server.py")],
    )

    # 2. Connect to GitHub MCP Server (or Mock Server if Token not provided)
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if github_token:
        print("Connecting to Official GitHub MCP Server via npx...")
        await client.connect_to_server(
            name="github_mcp_server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": github_token},
        )
    else:
        print("⚠️ GITHUB_PERSONAL_ACCESS_TOKEN not set. Falling back to Mock GitHub MCP Server...")
        await client.connect_to_server(
            name="github_mcp_server",
            command=python_exec,
            args=[str(answer_dir / "github_mock_server.py")],
        )

    # 3. Read template resource from custom MCP Server
    template = await client.read_resource("release_notes_server", "release://templates/standard")
    print(f"\n📖 Loaded Resource (release://templates/standard):\n{template}\n")

    # 4. User Prompt
    prompt = (
        "リポジトリ 'miwaihnt/advanced-data-and-ai-engineering' のマージ済み Pull Request 一覧を取得してください。"
        "取得したPR情報を元に、バージョン 'v1.2.0' (タイトル: 'Vector Search & MCP Backpressure Fix') のリリースノートを作成してください。"
        "作成したら、必ず 'save_release_note' ツールを呼び出して保存まで完了させてください。"
    )

    print(f"👤 User Request:\n{prompt}\n")
    print("------------------ Agent Thinking & Execution ------------------")

    result = await client.chat_with_ollama(
        prompt=prompt,
        system_prompt="あなたは優秀なリリースエンジニアです。与えられたMCPツールを活用して情報を取得・加工・保存してください。",
    )

    print("\n------------------ Final Agent Output ------------------")
    print(result)
    print("============================================================")


if __name__ == "__main__":
    asyncio.run(main())
