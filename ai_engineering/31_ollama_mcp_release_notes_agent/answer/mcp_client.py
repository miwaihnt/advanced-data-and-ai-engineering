"""Multi-Server MCP Client for Local Ollama integration.

Manages connection to multiple MCP servers (stdio transport), maps MCP tools
to Ollama Function Calling format, and executes agent loops.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI


class MultiMCPClient:
    """Manages connections to multiple MCP servers and coordinates with Ollama via OpenAI SDK."""

    def __init__(self, ollama_model: str = "qwen2.5:7b", ollama_host: str = "http://localhost:11434"):
        self.ollama_model = ollama_model
        self.ollama_host = ollama_host
        self.openai_client = AsyncOpenAI(base_url=f"{ollama_host}/v1", api_key="ollama")
        self.sessions: Dict[str, ClientSession] = {}
        self.tool_to_server: Dict[str, str] = {}
        self.mcp_tools: List[Dict[str, Any]] = []

    async def connect_to_server(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """Connect to an individual MCP Server via stdio."""
        server_params = StdioServerParameters(command=command, args=args, env=env)
        
        # We store transport & session context manager tasks
        read, write = await stdio_client(server_params).__aenter__()
        session = await ClientSession(read, write).__aenter__()
        await session.initialize()

        self.sessions[name] = session
        print(f"✅ Connected to MCP Server: '{name}'")

        # Refresh tool definitions
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            self.tool_to_server[tool.name] = name
            
            # Convert MCP Tool schema to OpenAI function calling schema
            ollama_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema if hasattr(tool, "inputSchema") else tool.input_schema,
                },
            }
            self.mcp_tools.append(ollama_tool)

    async def read_resource(self, server_name: str, uri: str) -> str:
        """Read a resource from a specific MCP Server."""
        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' not connected.")
        session = self.sessions[server_name]
        result = await session.read_resource(uri)
        contents = []
        for content in result.contents:
            if hasattr(content, "text"):
                contents.append(content.text)
        return "\n".join(contents)

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool on the appropriate MCP Server."""
        server_name = self.tool_to_server.get(tool_name)
        if not server_name:
            return f"Error: Tool '{tool_name}' not found on any connected MCP Server."

        session = self.sessions[server_name]
        try:
            result = await session.call_tool(tool_name, arguments=tool_args)
            output = []
            for content in result.content:
                if hasattr(content, "text"):
                    output.append(content.text)
            return "\n".join(output) if output else "Tool executed successfully with no text output."
        except Exception as e:
            return f"Error executing tool '{tool_name}' on server '{server_name}': {str(e)}"

    async def chat_with_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Execute agent loop between Ollama and connected MCP Servers using OpenAI SDK."""
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        while True:
            response = await self.openai_client.chat.completions.create(
                model=self.ollama_model,
                messages=messages,
                tools=self.mcp_tools if self.mcp_tools else None,
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # Append assistant message to history
            msg_dict: Dict[str, Any] = {"role": "assistant"}
            if response_message.content:
                msg_dict["content"] = response_message.content
            if tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": call.type,
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ]
            messages.append(msg_dict)

            if not tool_calls:
                # No further tool calls requested, return final response text
                return response_message.content or ""

            # Execute requested tool calls via MCP
            for call in tool_calls:
                fn_name = call.function.name
                fn_args_str = call.function.arguments
                fn_args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else fn_args_str

                print(f"🤖 Ollama requested Tool Call -> {fn_name}({fn_args})")
                tool_result = await self.execute_tool(fn_name, fn_args)
                print(f"🔧 MCP Server Output -> {tool_result[:150]}...")

                # Append tool result back to message history
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": tool_result,
                })

