#!/usr/bin/python
"""
Module 4: ツール利用 — MCP Step 2: FAQ 検索ツールの追加 演習ファイル

目標:
    Step 1 の echo ツールに加え、社内 FAQ を検索する search_faq ツールを実装する。

実行方法:
    python module4_mcp-step2.py

# EDIT HERE! 部分を埋めてください。
"""

from fastmcp import FastMCP

# サンプル FAQ データ（実際の演習では外部ファイルや DB から読み込む）
FAQ_DATA = [
    {"id": "faq-001", "question": "有給休暇の申請方法は？", "answer": "社内ポータルの「勤怠管理」メニューから申請してください。"},
    {"id": "faq-002", "question": "経費精算の締め切りはいつ？", "answer": "毎月末日が締め切りです。翌月5日までに承認を得てください。"},
    {"id": "faq-003", "question": "VPN の接続方法は？", "answer": "IT サポートページの手順書を参照してください。"},
    {"id": "faq-004", "question": "健康診断の予約方法は？", "answer": "人事部から送付されるメールのリンクから予約してください。"},
    {"id": "faq-005", "question": "社内Wi-Fiのパスワードは？", "answer": "受付にて社員証をご提示ください。セキュリティ上、メールでの案内はしておりません。"},
]

mcp = FastMCP("Axxx Japan社内ツールサーバー")


@mcp.tool()
def echo(message: str) -> str:
    """メッセージをそのまま返す"""
    return message


# EDIT HERE! search_faq ツールを実装してください。
# 関数名: search_faq
# 引数: query (str) — 検索キーワード
# 戻り値: str — マッチした FAQ のリスト（JSON 文字列形式）。マッチなしの場合は "該当する FAQ が見つかりませんでした。" を返す。
# docstring: "社内 FAQ をキーワードで検索する"
# ヒント: FAQ_DATA の question と answer に対して query が部分一致するものを抽出し、
#         json.dumps() で JSON 文字列に変換して返す。
#
# import json
#
# @mcp.tool()
# def search_faq(query: str) -> str:
#     """社内 FAQ をキーワードで検索する"""
#     ...


if __name__ == "__main__":
    mcp.run()
