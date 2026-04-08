#!/usr/bin/python
"""
step4 MCP クライアント（サンプル・モック版）


## このサンプルの特徴
- OpenAI / Azure トークン不要: LLM 部分をモックに置き換えてある
- MCP 接続部分は本物: 実際に SSE で MCP サーバーに接続し、ツールを発見・実行する
- 3 つのツールすべてを順番に試すデモシナリオを内蔵

ツールを追加・変更したいときは step4_mcp-server.py だけを変更すればよく、
このクライアントコードは一切変更不要。
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import logging

from mcp import ClientSession
from mcp.client.sse import sse_client

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MCP_SERVER_URL = "http://localhost:8000/sse"
#[remote]MCP_SERVER_URL = "https://support.atlassian.com/ja/rovo/docs/atlassian-remote-mcp-server/"


# ── モック LLM ──────────────────────────────────────────────────────────────
# OpenAI クライアントの代わりに使うモック。
# 実際の LLM と同じインターフェース（client.responses.create）を持つ。


@dataclass
class MockFunctionCall:
    """OpenAI ResponseFunctionToolCall のモック。

    execute_tool() が .name と .arguments を参照するため、同名の属性を持つ。
    """

    name: str
    arguments: str  # JSON 文字列
    type: str = "function_call"
    call_id: str = field(default_factory=lambda: f"mock_{uuid.uuid4().hex[:8]}")


@dataclass
class MockResponse:
    """OpenAI Response のモック。

    run_chat() が .output と .output_text を参照するため、同名の属性を持つ。
    """

    output: list
    output_text: str = ""


class MockLLMResponses:
    """OpenAI client.responses のモック。

    ユーザーメッセージのキーワードに基づき、どのツールを呼び出すかを決定する。
    本物の LLM の代わりに使うことで、API キーなしで動作確認できる。
    """

    # (検知キーワード群, ツール名, 引数) のルーティングテーブル
    _ROUTING: list[tuple[tuple[str, ...], str, dict]] = [
        (
            ("ローン", "返済", "月々", "月額", "借入"),
            "calculate_loan_monthly_payment",
            {"principal": 3_000_000, "annual_rate_percent": 1.5, "months": 120},
        ),
        (
            ("今日", "今", "日付", "日時", "時刻", "現在"),
            "get_current_datetime",
            {},
        ),
        (
            ("残り", "あと何日", "日数", "期限", "まであと"),
            "count_days_until",
            {"target_date_str": "2025-12-31"},
        ),
    ]

    def create(
        self,
        *,
        input: list,
        tools: list[dict[str, Any]],
        **_: Any,
    ) -> MockResponse:
        # ── フェーズ 2: ツール実行結果が含まれている → 要約テキストを返す ──
        tool_outputs = [
            m["output"]
            for m in input
            if isinstance(m, dict) and m.get("type") == "function_call_output"
        ]
        if tool_outputs:
            summary = "【モック回答】ツール実行結果:\n" + "\n---\n".join(tool_outputs)
            return MockResponse(output=[], output_text=summary)

        # ── フェーズ 1: 最後のユーザーメッセージを取得してキーワードマッチ ──
        user_msg = ""
        for msg in reversed(input):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        available = {t["name"] for t in tools}
        for keywords, tool_name, args in self._ROUTING:
            if tool_name not in available:
                continue
            if any(kw in user_msg for kw in keywords):
                logger.info(f"[MockLLM] ツール呼び出し決定: {tool_name}({args})")
                call = MockFunctionCall(
                    name=tool_name,
                    arguments=json.dumps(args, ensure_ascii=False),
                )
                return MockResponse(output=[call], output_text="")

        # マッチなし → ツールを使わずテキストで回答
        return MockResponse(
            output=[],
            output_text=f"[MockLLM] 「{user_msg}」に対応するツールが見つかりませんでした。",
        )


class MockLLMClient:
    """OpenAI クライアントのモック。responses 属性のみ実装。"""

    def __init__(self) -> None:
        self.responses = MockLLMResponses()


# ── MCP ユーティリティ（サンプルと同一） ────────────────────────────────────


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
    # MCP サーバーからツール一覧を取得
    tools_response = await session.list_tools()
    logger.info(f"MCP サーバーから {len(tools_response.tools)} 件のツールを取得しました")

    # MCP のツール定義を OpenAI のツール定義形式に変換
    # MCP ツールのプロパティ: tool.name / tool.description / tool.inputSchema（JSON Schema）
    # OpenAI ツールのプロパティ: type / name / description / strict / parameters（JSON Schema）
    openai_tools = []
    for tool in tools_response.tools:
        logger.info(f"  - {tool.name}: {tool.description}")
        openai_tools.append(
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description or "",
                "strict": False,
                "parameters": tool.inputSchema,
            }
        )
    return openai_tools


async def execute_tool(session: ClientSession, output: MockFunctionCall) -> str:
    """LLM が指定したツールを MCP サーバー経由で実行し、結果を文字列で返す。

    ここでは MCP クライアントを通じてサーバー側の関数を呼び出す。

    Args:
        session: 初期化済みの MCP クライアントセッション
        output: LLM からの function_call 出力（.name / .arguments を持つ）

    Returns:
        ツールの実行結果（テキスト）
    """
    args = json.loads(output.arguments)
    logger.info(f"MCP ツール実行: {output.name}({args})")

    # MCP サーバーにツール実行を委譲
    result = await session.call_tool(output.name, args)

    # 結果の取り出し（MCP では result.content がテキストブロックのリスト）
    return "\n".join(block.text for block in result.content if hasattr(block, "text"))


async def run_demo(client: MockLLMClient, session: ClientSession) -> None:
    """デモシナリオを自動実行する（対話なし）。

    MCP サーバーから動的にツールを取得し、3 種類のツールをすべて試す。
    """
    tools = await discover_tools(session)

    # デモ用の質問リスト（それぞれ異なるツールを呼び出す）
    demo_questions = [
        "今日の日付と現在時刻を教えてください",
        "借入300万円・年利1.5%・10年ローンの月々の返済額を計算してください",
        "2025年12月31日まであと何日残っていますか",
    ]

    instructions = "あなたは金融サービスに関する質問に答えるアシスタントです。"
    print("\n" + "=" * 60)
    print("MCP クライアント デモ（モック LLM 使用）")
    print("=" * 60)

    for question in demo_questions:
        print(f"\nUser: {question}")
        messages: list[Any] = [{"role": "user", "content": question}]

        # エージェントループ（最大 3 ターン）
        for _ in range(3):
            response = client.responses.create(
                instructions=instructions,
                input=messages,
                tools=tools,
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

    print("\n" + "=" * 60)
    print("デモ完了")
    print("=" * 60)


async def main() -> None:
    # MockLLMClient を使用（OpenAI トークン不要）
    client = MockLLMClient()

    # MCP サーバーへの接続
    # MCP サーバーに接続してツール一覧を取得するだけでよい
    logger.info(f"MCP サーバーに接続中... ({MCP_SERVER_URL})")
    async with sse_client(url=MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP セッション確立")
            await run_demo(client, session)


if __name__ == "__main__":
    # 初めて登場する asyncio.run()
    # MCP の SDK は非同期（async/await）で設計されているため、
    # エントリーポイントで asyncio.run() を使って非同期処理を起動する
    asyncio.run(main())
