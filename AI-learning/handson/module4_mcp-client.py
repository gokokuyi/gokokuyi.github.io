#!/usr/bin/python
"""
Module 4: ツール利用 — MCP クライアント 演習ファイル

目標:
    asyncio と OpenAI SDK (AsyncAzureOpenAI) を使い、
    MCP サーバー（module4_mcp-step3.sample.py）に接続して
    ツールを呼び出すクライアントを実装する。

事前準備:
    別ターミナルで MCP サーバーを起動しておいてください:
        python module4_mcp-step3.sample.py

実行方法:
    python module4_mcp-client.py

# EDIT HERE! 部分を埋めてください。
"""

import asyncio
import json

import yaml

# EDIT HERE! 必要なライブラリをインポートしてください。
# from openai import AsyncAzureOpenAI
# from utils.azure_auth import get_azure_token_provider


# EDIT HERE! config.yaml から Azure OpenAI クライアントを初期化する関数を実装してください。
# async def get_client() -> AsyncAzureOpenAI:
#     with open("config.yaml", "r", encoding="utf-8") as f:
#         config = yaml.safe_load(f)
#     client_config = config.get("OPENAI_CLIENT", {})
#     base_url = client_config.get("BASE_URL")
#     api_key = client_config.get("API_KEY", get_azure_token_provider())
#     return AsyncAzureOpenAI(base_url=base_url, api_key=api_key)


# MCP サーバーが公開するツールの定義（MCP クライアントが自動取得する想定だが、演習では手動で定義）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "echo",
            "description": "メッセージをそのまま返す",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "エコーするメッセージ"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": "社内 FAQ をキーワードで検索する",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索キーワード"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "問い合わせチケットを作成する",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "チケットのタイトル"},
                    "description": {"type": "string", "description": "問い合わせ内容の詳細"},
                    "category": {
                        "type": "string",
                        "description": "カテゴリ",
                        "enum": ["IT", "人事", "経理", "その他"],
                    },
                },
                "required": ["title", "description", "category"],
            },
        },
    },
]


def call_local_tool(tool_name: str, tool_args: dict) -> str:
    """ローカルで MCP ツールをモック呼び出しする（演習用スタブ）

    実際の MCP 統合では、MCP クライアントライブラリを通じてサーバーにリクエストします。
    この演習では理解のため、ツールの動作をローカルで再現します。
    """
    if tool_name == "echo":
        return tool_args.get("message", "")
    elif tool_name == "search_faq":
        query = tool_args.get("query", "")
        # モックレスポンス
        return f"「{query}」に関する FAQ: 社内ポータルをご確認ください。"
    elif tool_name == "create_ticket":
        return json.dumps({
            "ticket_id": "mock-0001",
            "title": tool_args.get("title", ""),
            "description": tool_args.get("description", ""),
            "category": tool_args.get("category", "その他"),
            "status": "open",
            "created_at": "2026-04-17T00:00:00",
        }, ensure_ascii=False, indent=2)
    else:
        return f"Unknown tool: {tool_name}"


async def chat(user_input: str) -> None:
    """ユーザー入力を受け取り、LLM + MCP ツールで応答する"""
    # EDIT HERE! AsyncAzureOpenAI クライアントを初期化してください。
    # client = await get_client()

    messages = [{"role": "user", "content": user_input}]

    # EDIT HERE! client.chat.completions.create() を呼び出し、tools を渡してください。
    # response = await client.chat.completions.create(
    #     model="gpt-5-nano",  # config.yaml の MODEL に合わせてください
    #     messages=messages,
    #     tools=TOOLS,
    #     tool_choice="auto",
    # )

    # EDIT HERE! レスポンスにツール呼び出しが含まれていれば実行し、結果を messages に追加して再度 LLM を呼び出してください。
    # ヒント:
    #   response.choices[0].message.tool_calls でツール呼び出しリストを取得できます。
    #   各 tool_call は tool_call.function.name と tool_call.function.arguments を持ちます。
    #   ツール実行結果は role="tool", tool_call_id=tool_call.id, content=result として messages に追加します。

    print(f"Assistant: （ここに LLM の応答が入ります）")


async def main() -> None:
    print("MCP クライアント起動 (`q` または `quit` で終了)")
    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ["q", "quit"]:
            break
        if not user_input:
            continue
        await chat(user_input)


if __name__ == "__main__":
    asyncio.run(main())
