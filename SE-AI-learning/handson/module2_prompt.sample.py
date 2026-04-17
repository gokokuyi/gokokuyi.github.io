"""
Module 2: プロンプト設計 — 解答例
module2_prompt.py の完成版サンプルです。
実行: python module2_prompt.sample.py --step 1
"""
import argparse
import json
import sys
import yaml
from pathlib import Path


def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("config.yaml が見つかりません。")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_client(config):
    from openai import AzureOpenAI
    from utils.azure_auth import get_azure_token_provider
    token_provider = get_azure_token_provider()
    return AzureOpenAI(
        azure_endpoint=config["azure_endpoint"],
        azure_ad_token_provider=token_provider,
        api_version=config.get("api_version", "2025-01-01"),
    ), config.get("model", "gpt-4o")


def step1(config):
    print("=" * 60)
    print("Step 1: 構造化出力（JSON形式）— 解答例")
    print("=" * 60)

    client, model = get_client(config)

    instructions = """
# タスク
ユーザーからの社内問い合わせを分析し、以下の JSON 形式のみで返してください。
JSON 以外のテキストは一切含めないでください。

# 出力形式
{
  "category": "技術/人事/経費/その他",
  "urgency": "high/medium/low",
  "summary": "問い合わせの要約（30文字以内）",
  "suggested_action": "推奨対応（例: IT部門へ連絡、申請フォームで手続き等）"
}

# urgency の判断基準
- high: 業務が完全に停止している、または多数ユーザーに影響
- medium: 業務に支障があるが一部は継続可能
- low: 情報確認・手続き・改善要望
"""

    test_queries = [
        "メールが朝から全く送れない状態です。至急対応をお願いします。",
        "来月からテレワーク申請の方法が変わると聞きましたが、手順を教えてください。",
        "先月の出張費の精算がまだ処理されていないようです。",
    ]

    for query in test_queries:
        print(f"\n入力: {query}")
        response = client.responses.create(model=model, instructions=instructions, input=query)
        output = response.output_text.strip()
        print(f"出力: {output}")
        try:
            parsed = json.loads(output)
            print(f"  ✅ category={parsed.get('category')}, urgency={parsed.get('urgency')}")
        except json.JSONDecodeError:
            print("  ❌ JSON ではありません")


def step2(config):
    print("=" * 60)
    print("Step 2: タスク / 評価基準 / 禁止事項の明記 — 解答例")
    print("=" * 60)

    client, model = get_client(config)

    instructions_a = "あなたは優秀なコードレビュアーです。"

    instructions_b = """
# タスク
提供された Python コードのレビューを実施してください。

# 評価基準（この順番で優先）
1. セキュリティリスク（SQLインジェクション、機密情報のハードコード等）
2. パフォーマンスの問題（非効率なループ、不必要なメモリ使用等）
3. PEP8 / コーディング規約の違反

# 禁止事項
- 推測による断定的な指摘をしない（「可能性がある」と明記する）
- 3点以上の指摘がある場合は優先度順に整理する
- コードの動作目的が不明な部分は質問として記載する

# 出力形式
各指摘を以下の形式で箇条書きにする:
指摘N: [重要度: 高/中/低] 問題点の説明 → 改善案
"""

    code_sample = """
import os
password = os.environ.get('DB_PASSWORD', 'admin123')

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)

def process_list(items):
    result = []
    for i in range(len(items)):
        result = result + [items[i] * 2]
    return result
"""

    print("\n--- パターン A（役割付与のみ）---")
    resp_a = client.responses.create(model=model, instructions=instructions_a,
                                      input=f"以下のコードをレビューしてください:\n{code_sample}")
    print(resp_a.output_text[:500] + "..." if len(resp_a.output_text) > 500 else resp_a.output_text)

    print("\n--- パターン B（タスク/評価基準/禁止事項あり）---")
    resp_b = client.responses.create(model=model, instructions=instructions_b,
                                      input=f"以下のコードをレビューしてください:\n{code_sample}")
    print(resp_b.output_text[:500] + "..." if len(resp_b.output_text) > 500 else resp_b.output_text)


def step3(config):
    print("=" * 60)
    print("Step 3: Few-shot プロンプト — 解答例")
    print("=" * 60)

    client, model = get_client(config)

    instructions_zero = "インシデントチケットのタイトルを、優先度と分類を含む形式に変換してください。"

    examples = [
        {"input": "ログイン画面が表示されない",        "output": "[P1][UI障害] ログイン画面が表示されない"},
        {"input": "レポートのソートが遅い",             "output": "[P3][性能] レポートソート処理の遅延"},
        {"input": "請求書PDFのダウンロードでエラー",    "output": "[P2][機能障害] 請求書PDFダウンロードエラー"},
    ]

    few_shot_examples = "\n".join(
        [f"入力: {e['input']}\n出力: {e['output']}" for e in examples]
    )

    instructions_few = f"""
インシデントチケットのタイトルを "[P{{優先度}}][{{分類}}] {{簡潔タイトル}}" 形式に変換してください。

優先度: P1=緊急(業務停止)、P2=重要(業務に支障)、P3=通常(軽微)
分類: UI障害/機能障害/性能/セキュリティ/申請・手続き/その他

# 変換例
{few_shot_examples}

出力は変換後のタイトルのみ（1行）で返してください。
"""

    test_inputs = [
        "夜間バッチが昨夜から停止している",
        "社員証のICカード読み取りが反応しない",
        "給与明細の金額が先月と同じになっている",
    ]

    for user_input in test_inputs:
        print(f"\n入力: {user_input}")
        resp_zero = client.responses.create(model=model, instructions=instructions_zero, input=user_input)
        print(f"  Zero-shot: {resp_zero.output_text.strip()}")
        resp_few = client.responses.create(model=model, instructions=instructions_few, input=user_input)
        print(f"  Few-shot:  {resp_few.output_text.strip()}")


def step4(config):
    print("=" * 60)
    print("Step 4: Structured Outputs — 解答例")
    print("=" * 60)

    client, model = get_client(config)

    system_prompt = """
以下の JSON スキーマで返してください（JSON 以外の出力は禁止）:
{
  "ticket_id": "<INC-XXXの形式>",
  "title": "<タイトル>",
  "priority": "<P1/P2/P3>",
  "category": "<UI障害/機能障害/性能/セキュリティ/その他>",
  "assignee": "<担当チーム名>"
}
"""

    incident = "本番環境のAPIサーバーが503エラーを返しており、全ユーザーがサービスを利用できない状態です。"
    print(f"入力インシデント: {incident}\n")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": incident},
        ],
        response_format={"type": "json_object"},   # ← 型を強制
    )
    output = response.choices[0].message.content
    print(f"生の出力:\n{output}\n")

    try:
        ticket = json.loads(output)
        print("✅ JSON パース成功:")
        for key, value in ticket.items():
            print(f"  {key}: {value}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON パースエラー: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="module2_prompt.sample.py — プロンプト設計 解答例")
    parser.add_argument("--step", type=int, default=1, choices=[1, 2, 3, 4])
    args = parser.parse_args()

    config = load_config()

    if args.step == 1:
        step1(config)
    elif args.step == 2:
        step2(config)
    elif args.step == 3:
        step3(config)
    elif args.step == 4:
        step4(config)
