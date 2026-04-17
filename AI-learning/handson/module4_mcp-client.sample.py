#!/usr/bin/python
"""
Module 4: ツール利用 — MCP クライアント サンプル解答

このファイルは MCP クライアント演習の完成形サンプルです。演習後に確認してください。

事前準備:
    別ターミナルで MCP サーバーを起動しておいてください:
        python module4_mcp-step3.sample.py

実行方法:
    python module4_mcp-client.sample.py
"""

import asyncio
import json

import yaml
from openai import AsyncAzureOpenAI

from utils.azure_auth import get_azure_token_provider


async def get_client() -> AsyncAzureOpenAI:
    """config.yaml から Azure OpenAI 非同期クライアントを初期化する"""
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    client_config = config.get("OPENAI_CLIENT", {})
    base_url = client_config.get("BASE_URL")
    if base_url is None:
        raise ValueError("`OPENAI_CLIENT` の `BASE_URL` が設定されていません。config.yaml を確認してください。")
    api_key = client_config.get("API_KEY", get_azure_token_provider())
    return AsyncAzureOpenAI(base_url=base_url, api_key=api_key)


# MCP サーバーが公開するツールの定義（演習では手動で定義）
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

# サンプル FAQ データ（MCP サーバーと同一データ — 本来はサーバー側で処理）
_FAQ_DATA = [
    {"id": "faq-001", "question": "有給休暇の申請方法は？", "answer": "社内ポータルの「勤怠管理」メニューから申請してください。"},
    {"id": "faq-002", "question": "経費精算の締め切りはいつ？", "answer": "毎月末日が締め切りです。翌月5日までに承認を得てください。"},
    {"id": "faq-003", "question": "VPN の接続方法は？", "answer": "IT サポートページの手順書を参照してください。"},
    {"id": "faq-004", "question": "健康診断の予約方法は？", "answer": "人事部から送付されるメールのリンクから予約してください。"},
    {"id": "faq-005", "question": "社内Wi-Fiのパスワードは？", "answer": "受付にて社員証をご提示ください。セキュリティ上、メールでの案内はしておりません。"},
]
_ticket_store: list[dict] = []


def call_local_tool(tool_name: str, tool_args: dict) -> str:
    """ローカルで MCP ツールを呼び出す（演習用スタブ）

    実際の MCP 統合では、MCP クライアントライブラリを通じてサーバーにリクエストします。
    """
    import uuid
    from datetime import datetime

    if tool_name == "echo":
        return tool_args.get("message", "")

    elif tool_name == "search_faq":
        query = tool_args.get("query", "")
        results = [
            faq for faq in _FAQ_DATA
            if query in faq["question"] or query in faq["answer"]
        ]
        if not results:
            return "該当する FAQ が見つかりませんでした。"
        return json.dumps(results, ensure_ascii=False, indent=2)

    elif tool_name == "create_ticket":
        ticket = {
            "ticket_id": str(uuid.uuid4())[:8],
            "title": tool_args.get("title", ""),
            "description": tool_args.get("description", ""),
            "category": tool_args.get("category", "その他"),
            "status": "open",
            "created_at": datetime.now().isoformat(),
        }
        _ticket_store.append(ticket)
        return json.dumps(ticket, ensure_ascii=False, indent=2)

    else:
        return f"Unknown tool: {tool_name}"


async def chat(client: AsyncAzureOpenAI, model: str, user_input: str) -> None:
    """ユーザー入力を受け取り、LLM + MCP ツールで応答する"""
    messages = [{"role": "user", "content": user_input}]

    # LLM に初回リクエスト（ツール定義を渡す）
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    assistant_message = response.choices[0].message
    messages.append(assistant_message)

    # ツール呼び出しがある間はループ
    while assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"[Tool] {tool_name}({tool_args})")
            tool_result = call_local_tool(tool_name, tool_args)

            # ツール実行結果を messages に追加
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

        # ツール結果を踏まえて再度 LLM を呼び出す
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        assistant_message = response.choices[0].message
        messages.append(assistant_message)

    print(f"Assistant: {assistant_message.content}")


async def main() -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    model = config.get("OPENAI_CLIENT", {}).get("PARAMETERS", {}).get("MODEL", "gpt-5-nano")

    client = await get_client()
    print("MCP クライアント起動 (`q` または `quit` で終了)")

    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ["q", "quit"]:
            break
        if not user_input:
            continue
        await chat(client, model, user_input)


if __name__ == "__main__":
    asyncio.run(main())
