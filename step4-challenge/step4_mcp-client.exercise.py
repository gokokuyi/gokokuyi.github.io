#!/usr/bin/python
"""
step4 exercise MCP クライアント（演習ファイル）

事前に step4_mcp-server.py を起動しておくこと:
    cd src/handson && python step4_mcp-server.py

## EDIT HERE 一覧（3箇所）
- EDIT HERE ①（低）  : session.list_tools() でツール一覧を取得
- EDIT HERE ②（中）  : MCP ツール定義を OpenAI ツール定義形式に変換
- EDIT HERE ③（低）  : session.call_tool() でツールを実行し、結果を取り出す
"""
import asyncio
import json
import textwrap
from typing import Any

import yaml
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
from openai.types.responses import ResponseFunctionToolCall

from utils.azure_auth import get_azure_token_provider
from utils.logger import get_logger

logger = get_logger()

MCP_SERVER_URL = "http://localhost:8000/sse"


def build_openai_client(config: dict[str, Any]) -> tuple[OpenAI, dict[str, Any]]:
    """config.yaml から OpenAI クライアントとパラメータを構築する。"""
    client_config = config.get("OPENAI_CLIENT", {})
    base_url = client_config.get("BASE_URL")
    if base_url is None:
        raise ValueError("`OPENAI_CLIENT` の `BASE_URL` が設定されていません。config.yaml を確認してください。")
    api_key = client_config.get("API_KEY", get_azure_token_provider())
    client = OpenAI(base_url=base_url, api_key=api_key)

    params_config = client_config.get("PARAMETERS", {})
    params = {
        "model": params_config.get("MODEL", "gpt-5-nano"),
        "text": {"verbosity": params_config.get("VERBOSITY", "low")},
        "reasoning": {
            "effort": params_config.get("REASONING", {}).get("EFFORT", "low"),
            "summary": params_config.get("REASONING", {}).get("SUMMARY", "auto"),
        },
        "max_output_tokens": params_config.get("MAX_OUTPUT_TOKENS", ""),
    }
    params = {k: v for k, v in params.items() if v}
    return client, params


async def discover_tools(session: ClientSession) -> list[dict[str, Any]]:
    """MCP サーバーからツール一覧を取得し、OpenAI のツール形式に変換する。

    ここでは MCP サーバーに
    問い合わせて動的に取得する。サーバー側でツールを追加・変更しても、
    このクライアントコードは変更不要。

    Args:
        session: 初期化済みの MCP クライアントセッション

    Returns:
        OpenAI の Responses API に渡せる形式のツール定義リスト
    """
    # EDIT HERE ①: MCP サーバーからツール一覧を取得してください
    # ヒント: session.list_tools() を await で呼び出すと、
    #         tools_response.tools にツールオブジェクトのリストが入ります
    #   tools_response = await session.list_tools()
    tools_response = ...

    logger.info(f"MCP サーバーから {len(tools_response.tools)} 件のツールを取得しました")

    # EDIT HERE ②: MCP のツール定義を OpenAI のツール定義形式に変換してください
    # MCP ツールのプロパティ   : tool.name / tool.description / tool.inputSchema
    # OpenAI ツールのプロパティ: type / name / description / strict / parameters
    #
    # ヒント:
    #   openai_tools = []
    #   for tool in tools_response.tools:
    #       logger.info(f"  - {tool.name}: {tool.description}")
    #       openai_tools.append({
    #           "type": "function",
    #           "name": tool.name,
    #           "description": tool.description or "",
    #           "strict": False,
    #           "parameters": tool.inputSchema,
    #       })
    #   return openai_tools
    openai_tools = ...
    return openai_tools


async def execute_tool(session: ClientSession, output: ResponseFunctionToolCall) -> str:
    """LLM が指定したツールを MCP サーバー経由で実行し、結果を文字列で返す。

    ここでは MCP クライアントを通じてサーバー側の関数を呼び出す。

    Args:
        session: 初期化済みの MCP クライアントセッション
        output: LLM からの function_call 出力

    Returns:
        ツールの実行結果（テキスト）
    """
    args = json.loads(output.arguments)
    logger.info(f"MCP ツール実行: {output.name}({args})")

    # EDIT HERE ③: MCP サーバーにツール実行を委譲し、結果のテキストを取り出してください
    # ヒント:
    #   result = await session.call_tool(output.name, args)
    #   # result.content はテキストブロックのリスト。各ブロックの .text 属性がテキスト本文
    #   return "\n".join(block.text for block in result.content if hasattr(block, "text"))
    result = ...
    return ...


async def run_chat(client: OpenAI, params: dict[str, Any], session: ClientSession) -> None:
    """エージェントループを含むチャット本体。"""
    tools = await discover_tools(session)

    instructions = """
    ## 役割
    あなたは金融サービスに関する質問に答える、優秀なアシスタントです。

    ## スキル
    ローン計算・日付計算・現在時刻の取得などに関するツールを利用することができます。

    ## タスク
    ユーザからの質問に対して、必要に応じてツールを呼び出しながら、正確でわかりやすい回答を提供してください。

    ## 制約
    - 計算が必要な場合は必ずツールを使い、自分で暗算した結果を答えてはなりません
    - ツールの結果をそのまま貼り付けるのではなく、自然な日本語で回答してください
    """
    instructions = textwrap.dedent(instructions).strip()
    messages: list[dict[str, Any]] = []
    logger.info("`q` または `quit` で終了")

    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ["q", "quit"]:
            break
        if user_input == "":
            continue

        messages.append({"role": "user", "content": user_input})

        # エージェントループ
        # 違い: ツールの実行が「自分の Python 関数呼び出し」→「MCP サーバー経由」になっただけ
        max_turns = 5
        for turn in range(max_turns):
            response = client.responses.create(
                instructions=instructions,
                input=messages,
                tools=tools,
                **params,
            )
            messages += response.output

            tool_called = False
            for output in response.output:
                if output.type != "function_call":
                    continue
                tool_called = True
                tool_result = await execute_tool(session, output)
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": output.call_id,
                        "output": tool_result,
                    }
                )

            if not tool_called:
                break

        if response.output_text:
            print(f"Assistant: {response.output_text}")

    logger.info("Bye")


async def main() -> None:
    # config.yaml の読み込み
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    client, params = build_openai_client(config)

    # MCP サーバーへの接続
    # MCP サーバーに接続してツール一覧を取得するだけでよい
    logger.info(f"MCP サーバーに接続中... ({MCP_SERVER_URL})")
    async with sse_client(url=MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP セッション確立")
            await run_chat(client, params, session)


if __name__ == "__main__":
    # 初めて登場する asyncio.run()
    # MCP の SDK は非同期（async/await）で設計されているため、
    # エントリーポイントで asyncio.run() を使って非同期処理を起動する
    asyncio.run(main())
