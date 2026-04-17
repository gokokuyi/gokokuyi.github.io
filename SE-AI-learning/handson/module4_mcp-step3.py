#!/usr/bin/python
"""
Module 4: ツール利用 — MCP Step 3: チケット作成ツールの追加 演習ファイル

目標:
    Step 2 の echo + search_faq ツールに加え、問い合わせチケットを作成する
    create_ticket ツールを実装する。

実行方法:
    python module4_mcp-step3.py

# EDIT HERE! 部分を埋めてください。
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


# EDIT HERE! create_ticket ツールを実装してください。
# 関数名: create_ticket
# 引数:
#   - title (str): チケットのタイトル
#   - description (str): 問い合わせ内容の詳細
#   - category (str): カテゴリ（例: "IT", "人事", "経理", "その他"）
# 戻り値: str — 作成されたチケット情報の JSON 文字列
# docstring: "問い合わせチケットを作成する"
# ヒント:
#   - ticket_id は uuid.uuid4() で生成する（先頭8文字のみ使用: str(uuid.uuid4())[:8]）
#   - created_at は datetime.now().isoformat() で取得する
#   - status は "open" で固定する
#   - 作成したチケット辞書を _ticket_store.append() で保存する
#   - json.dumps() で JSON 文字列にして返す
#
# @mcp.tool()
# def create_ticket(title: str, description: str, category: str) -> str:
#     """問い合わせチケットを作成する"""
#     ...


if __name__ == "__main__":
    mcp.run()
