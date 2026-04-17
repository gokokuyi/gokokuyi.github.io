#!/usr/bin/python
"""
Module 4: ツール利用 — MCP Step 3: チケット作成ツールの追加 サンプル解答

このファイルは Step 3 の完成形サンプルです。演習後に確認してください。

実行方法:
    python module4_mcp-step3.sample.py
"""

import json
import uuid
from datetime import datetime

from fastmcp import FastMCP

# サンプル FAQ データ
FAQ_DATA = [
    {"id": "faq-001", "question": "有給休暇の申請方法は？", "answer": "社内ポータルの「勤怠管理」メニューから申請してください。"},
    {"id": "faq-002", "question": "経費精算の締め切りはいつ？", "answer": "毎月末日が締め切りです。翌月5日までに承認を得てください。"},
    {"id": "faq-003", "question": "VPN の接続方法は？", "answer": "IT サポートページの手順書を参照してください。"},
    {"id": "faq-004", "question": "健康診断の予約方法は？", "answer": "人事部から送付されるメールのリンクから予約してください。"},
    {"id": "faq-005", "question": "社内Wi-Fiのパスワードは？", "answer": "受付にて社員証をご提示ください。セキュリティ上、メールでの案内はしておりません。"},
]

# チケットの一時保存領域（実際の運用では DB を使用）
_ticket_store: list[dict] = []

mcp = FastMCP("Axxx Japan社内ツールサーバー")


@mcp.tool()
def echo(message: str) -> str:
    """メッセージをそのまま返す"""
    return message


@mcp.tool()
def search_faq(query: str) -> str:
    """社内 FAQ をキーワードで検索する"""
    results = [
        faq for faq in FAQ_DATA
        if query in faq["question"] or query in faq["answer"]
    ]
    if not results:
        return "該当する FAQ が見つかりませんでした。"
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def create_ticket(title: str, description: str, category: str) -> str:
    """問い合わせチケットを作成する"""
    ticket = {
        "ticket_id": str(uuid.uuid4())[:8],
        "title": title,
        "description": description,
        "category": category,
        "status": "open",
        "created_at": datetime.now().isoformat(),
    }
    _ticket_store.append(ticket)
    return json.dumps(ticket, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
