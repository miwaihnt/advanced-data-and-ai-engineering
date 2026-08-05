# 31. Ollama ✕ GitHub MCP ✕ 自作 FastMCP リリースノート自動生成エージェント

ローカルで動く LLM (**Ollama**) と、外部の標準プロトコルサーバー (**GitHub MCP Server**) および **自作の FastMCP Server** を統合し、リポジトリの変更履歴（PR/Commit）からリリースノートを自動生成・検証・保存するマルチ MCP システムを構築します。

---

## 🎯 学習目標 (Learning Objectives)

1. **MCP (Model Context Protocol) のアーキテクチャ理解**
   - Client / Server 分離構造と `stdio` (標準入出力) / `SSE` 通信プロトコルの仕組み
   - **Tools** (アクション実行) / **Resources** (コンテキスト提供) / **Prompts** (テンプレート) の違いと使い分け
2. **FastMCP によるカスタム MCP Server 自作**
   - Python の `fastmcp` ライブラリを使用したツール (`@mcp.tool()`) やリソース (`@mcp.resource()`) の定義方法
3. **Multi-Server MCP Client の構築**
   - Python `mcp` SDK を用い、複数の独立した MCP サーバーを接続してツールを集約・バインドする手法
4. **Ollama (Local LLM) Function Calling 連携**
   - MCP サーバーから取得したツールスキーマを Ollama の Tool Call フォーマットに動的変換し、自律的な Tool Call 実行ループを実装

---

## 🏗 システムアーキテクチャ

```
                                  +------------------------------------+
                                  |   GitHub MCP Server                |
                                  |   (npx @modelcontextprotocol/...  |
                                  |    Stdio / Tools: list_prs, etc)   |
                                  +-----------------+------------------+
                                                    ^
                                                    | (stdio transport)
+-------------------+     Tool Calls / Context      |
|                   | <----------------------> +----+------------------------+
|   Local Ollama    |                          |                         |
| (qwen2.5 / llama3)|                          |  Multi-MCP Client       |
|                   | <----------------------> |  (Python asyncio / mcp) |
+-------------------+    Final Generated Response  |                         |
                                               +----+------------------------+
                                                    | (stdio transport)
                                                    v
                                  +-----------------+------------------+
                                  |   自作 FastMCP Server              |
                                  |   (custom_mcp_server.py)           |
                                  |   Tools: save_release_note         |
                                  |   Resources: release://templates/..|
                                  +------------------------------------+
```

---

## 📂 ディレクトリ構成

```text
31_ollama_mcp_release_notes_agent/
├── README.md                      # 本ドキュメント
├── requirements.txt               # 依存ライブラリ一覧
├── output/                        # 生成されたリリースノート(MD/JSON)の保存先
└── answer/
    ├── custom_mcp_server.py       # FastMCP を用いた自作 MCP サーバー
    ├── github_mock_server.py      # トークン未設定時に動作する GitHub MCP モックサーバー
    ├── mcp_client.py              # 複数 MCP サーバーを統合する MultiMCPClient
    ├── main.py                    # メイン実行スクリプト
    └── test_flow.py               # 単体テストスクリプト
```

---

## 🚀 クイックスタート & 実行手順

### 1. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2. 単体テストの実行

自作 FastMCP サーバーのツール動作を確認します。

```bash
pytest answer/test_flow.py -v
```

### 3. エージェントの実行

ローカルの Ollama (`qwen2.5:7b` 等) が起動していることを確認の上、以下を実行します。

```bash
# （任意）実際の GitHub リポジトリを読む場合
export GITHUB_PERSONAL_ACCESS_TOKEN="your_github_token"
export OLLAMA_MODEL="qwen2.5:7b"

# 実行
python answer/main.py
```

※ `GITHUB_PERSONAL_ACCESS_TOKEN` が未設定の場合は、自動的に安全な **Mock GitHub MCP Server** が起動するため、トークンなしでも動作確認が可能です！

---

## 💡 MCP (Model Context Protocol) 核心解説

### 1. MCP Tools と Resources の使い分け

- **Tools (動的アクション)**: 引数を受け取り、副作用（ファイル保存、API呼び出し、計算など）を発生させる関数。
  ```python
  @mcp.tool()
  def save_release_note(version: str, title: str, summary: str) -> str:
      ...
  ```
- **Resources (静的/状態コンテキスト)**: URI 形式 (`release://templates/standard`) で参照され、LLM や Client に静的テンプレートや状態をリードオンリーで共有するデータ。
  ```python
  @mcp.resource("release://templates/standard")
  def get_standard_template() -> str:
      ...
  ```

### 2. Multi-Server 統合の仕組み

`mcp_client.py` では、複数 MCP サーバーから取得した `Tool` オブジェクトの `inputSchema` を解析し、Ollama が解釈可能な OpenAI 互換 Function Calling JSON に変換して束ねています。

```python
# MCP Tool -> Ollama Function Schema 変換
ollama_tool = {
    "type": "function",
    "function": {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.inputSchema,
    },
}
```

---

## 🎓 演習課題 (Hands-on Challenge)

1. **新しい自作 MCP ツールの追加**:
   `custom_mcp_server.py` に `send_slack_notification_mock(channel: str, message: str)` ツールを追加し、リリースノート保存後にモックで通知ログを出力させてみましょう。
2. **Prompts 機能の拡張**:
   `FastMCP` の `@mcp.prompt()` デコレータを使用して、特定のリリースタイプ（メジャー/マイナー/パッチ）に応じたシステムプロンプトを提供する機能を追加してみましょう。
