#!/usr/bin/python
"""
step4 MCP サーバー

このファイルは step4_mcp-client.py から接続される MCP (Model Context Protocol) サーバー。
EDIT HERE はなし。受講者はこのファイルを変更せず、そのまま起動して使用する。

## 起動方法
    cd src/handson
    python step4_mcp-server.py

## 確認方法
    起動後に http://localhost:8000/sse にアクセスすると SSE ストリームが確認できる

## MCP とは
    LLM がツールを呼び出すための共通プロトコル（Model Context Protocol）。
    MCP ではその役割を専用サーバーに分離する。

    クライアント（LLM を呼ぶ側）はサーバーに接続するだけでツール一覧を取得でき、
    ツールの実装がどの言語・どのホストにあるかを意識しなくてよくなる。
"""
from datetime import date, datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SxxxFinanceTools")


@mcp.tool()
def get_current_datetime() -> str:
    """現在の日付と時刻を返す。

    ユーザーから「今日は何日？」「現在時刻は？」といった質問があった場合に使用する。

    Returns:
        現在の日付・時刻を "YYYY-MM-DD HH:MM:SS" 形式の文字列で返す
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool()
def calculate_loan_monthly_payment(principal: float, annual_rate_percent: float, months: int) -> str:
    """元利均等返済方式での毎月の返済額を計算する。

    住宅ローン・自動車ローンなど、一般的なローンの月々の返済額を求める際に使用する。

    Args:
        principal: 借入元金（円）
        annual_rate_percent: 年利（%）。例：2.5 → 年利 2.5%
        months: 返済期間（ヶ月）。例：240 → 20年

    Returns:
        毎月の返済額・返済総額・支払利息合計を含む文字列
    """
    if annual_rate_percent == 0:
        monthly_payment = principal / months
        total_payment = monthly_payment * months
        total_interest = 0.0
    else:
        monthly_rate = annual_rate_percent / 100 / 12
        monthly_payment = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        total_payment = monthly_payment * months
        total_interest = total_payment - principal

    return (
        f"借入元金: {principal:,.0f} 円\n"
        f"年利: {annual_rate_percent} %\n"
        f"返済期間: {months} ヶ月（{months // 12} 年）\n"
        f"毎月の返済額: {monthly_payment:,.0f} 円\n"
        f"返済総額: {total_payment:,.0f} 円\n"
        f"支払利息合計: {total_interest:,.0f} 円"
    )


@mcp.tool()
def count_days_until(target_date_str: str) -> str:
    """今日から指定した日付までの残り日数を計算する。

    キャンペーン期限・契約満了日など、特定の日までの日数を確認する際に使用する。

    Args:
        target_date_str: 対象の日付（"YYYY-MM-DD" 形式）。例："2025-12-31"

    Returns:
        今日から対象日付までの残り日数を含む文字列
    """
    try:
        target = date.fromisoformat(target_date_str)
    except ValueError:
        return f"日付の形式が正しくありません。'YYYY-MM-DD' 形式で指定してください。（入力値: {target_date_str}）"

    today = date.today()
    delta = (target - today).days

    if delta > 0:
        return f"今日（{today}）から {target_date_str} まで、あと {delta} 日です。"
    elif delta == 0:
        return f"今日（{today}）が {target_date_str} です。"
    else:
        return f"{target_date_str} は {abs(delta)} 日前（{today} 時点）です。"


if __name__ == "__main__":
    print("MCP サーバーを起動します（http://localhost:8000/sse）")
    print("停止するには Ctrl+C を押してください\n")
    mcp.run(transport="sse")
