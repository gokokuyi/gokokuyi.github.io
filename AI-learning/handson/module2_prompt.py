"""
Module 2: プロンプト設計 — 演習ファイル
各ステップの # EDIT HERE! 部分を埋めてください。
実行: python module2_prompt.py --step 1
"""
import argparse
import json
import sys
import yaml
from pathlib import Path


# ── 設定読み込み ───────────────────────────────────────────────────────────────
def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("config.yaml が見つかりません。handson/setup.html を参照してセットアップしてください。")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_client(config):
    from openai import OpenAI
    from utils.azure_auth import get_azure_token_provider
    client_cfg = config.get("OPENAI_CLIENT", {})
    base_url = client_cfg.get("BASE_URL")
    if not base_url:
        raise ValueError("config.yaml の OPENAI_CLIENT.BASE_URL が未設定です。setup.html を参照してください。")
    api_key = client_cfg.get("API_KEY", get_azure_token_provider())
    model = client_cfg.get("PARAMETERS", {}).get("MODEL", "gpt-4o")
    return OpenAI(base_url=base_url, api_key=api_key), model


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: 構造化出力 — JSON 形式で回答させる
# ═══════════════════════════════════════════════════════════════════════════════
def step1(config):
    """
    入力テキストを分析し、指定した JSON スキーマで返させるプロンプトを設計する。
    出力形式を明示することで、後続コードからの処理が容易になる。
    """
    print("=" * 60)
    print("Step 1: 構造化出力（JSON形式）")
    print("=" * 60)

    client, model = get_client(config)

    # EDIT HERE! 以下のシステムプロンプトを完成させてください。
    # 要件: ユーザーの問い合わせを以下の JSON 形式で返すよう指示する
    # {
    #   "category": "技術/人事/経費/その他",
    #   "urgency": "high/medium/low",
    #   "summary": "問い合わせの要約（30文字以内）",
    #   "suggested_action": "推奨対応"
    # }
    instructions = """
# タスク
ユーザーからの社内問い合わせを分析し、必ず以下の JSON 形式のみで返してください。
JSON 以外のテキスト（説明文・コードブロック記号等）は一切含めないでください。

# 出力形式
{
  "category": "EDIT HERE! 選択肢を列挙（例: 技術/人事/経費/その他）",
  "urgency":  "EDIT HERE! 判定基準を説明（例: high=業務停止/medium=支障あり/low=情報確認）",
  "summary":  "問い合わせの要約（30文字以内）",
  "suggested_action": "EDIT HERE! 推奨対応の例を1〜2個書く"
}
"""

    test_queries = [
        "メールが朝から全く送れない状態です。至急対応をお願いします。",
        "来月からテレワーク申請の方法が変わると聞きましたが、手順を教えてください。",
        "先月の出張費の精算がまだ処理されていないようです。",
    ]

    for query in test_queries:
        print(f"\n入力: {query}")
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=query,
        )
        output = response.output_text.strip()
        print(f"出力: {output}")
        # JSON としてパース確認
        try:
            parsed = json.loads(output)
            print(f"  ✅ JSON パース成功: category={parsed.get('category')}, urgency={parsed.get('urgency')}")
        except json.JSONDecodeError:
            print("  ❌ JSON ではありません。プロンプトを修正してください。")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: タスク / 評価基準 / 禁止事項を含むシステムプロンプト
# ═══════════════════════════════════════════════════════════════════════════════
def step2(config):
    """
    「役割付与」だけのプロンプトと、「タスク・評価基準・禁止事項」を明記した
    プロンプトを比較し、出力品質の違いを確認する。
    """
    print("=" * 60)
    print("Step 2: タスク / 評価基準 / 禁止事項の明記")
    print("=" * 60)

    client, model = get_client(config)

    # ── パターン A: 役割付与のみ（改善前）──────────────────────────────────
    instructions_a = "あなたは優秀なコードレビュアーです。"

    # ── パターン B: タスク・評価基準・禁止事項を明記（改善後）───────────────
    # EDIT HERE! 以下を埋めてください:
    # - タスク: Pythonコードのレビューを行う
    # - 評価基準: セキュリティリスク(優先)、パフォーマンス、PEP8準拠
    # - 禁止事項: 推測による断定的な指摘をしない、3点以上の指摘は優先度順に並べる
    # - 出力形式: 各指摘を「指摘N: [重要度] 問題点 → 改善案」の形式で
    instructions_b = """
# タスク
# EDIT HERE!

# 評価基準
# EDIT HERE!

# 禁止事項
# EDIT HERE!

# 出力形式
# EDIT HERE!
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

    print("\n💡 2つの出力を比較してみてください。どちらがより実用的ですか？")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Few-shot プロンプト — 例示による出力制御
# ═══════════════════════════════════════════════════════════════════════════════
def step3(config):
    """
    Few-shot 例をプロンプトに含めることで、特定の出力スタイルを学習させる。
    例示なし（Zero-shot）との比較で効果を確認する。
    """
    print("=" * 60)
    print("Step 3: Few-shot プロンプト")
    print("=" * 60)

    client, model = get_client(config)

    # ── ゼロショット ──────────────────────────────────────────────────────────
    instructions_zero = """
インシデントチケットのタイトルを、優先度と分類を含む形式に変換してください。
"""

    # ── Few-shot ─────────────────────────────────────────────────────────────
    # EDIT HERE! 以下の examples リストを使って Few-shot プロンプトを構築してください
    # 出力形式: "[P{1-3}][{分類}] {簡潔なタイトル}"
    examples = [
        {"input": "ログイン画面が表示されない",        "output": "[P1][UI障害] ログイン画面が表示されない"},
        {"input": "レポートのソートが遅い",             "output": "[P3][性能] レポートソート処理の遅延"},
        {"input": "請求書PDFのダウンロードでエラー",    "output": "[P2][機能障害] 請求書PDFダウンロードエラー"},
    ]

    instructions_few = """
インシデントチケットのタイトルを "[P{優先度}][{分類}] {簡潔タイトル}" 形式に変換してください。

# EDIT HERE! examples を使って Few-shot 指示を作成してください
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


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Structured Outputs — response_format で型を強制
# ═══════════════════════════════════════════════════════════════════════════════
def step4(config):
    """
    Chat Completions API の response_format={"type":"json_object"} を使い、
    JSON 出力を構造的に強制する。
    """
    print("=" * 60)
    print("Step 4: Structured Outputs（response_format）")
    print("=" * 60)

    client, model = get_client(config)

    # EDIT HERE! response_format={"type": "json_object"} を使って
    # 以下の仕様の JSON を返すよう実装してください:
    # {
    #   "ticket_id": "自動生成ID（例: INC-001）",
    #   "title": "タイトル",
    #   "priority": "P1/P2/P3",
    #   "category": "カテゴリ",
    #   "assignee": "担当チーム"
    # }

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

    # EDIT HERE! client.chat.completions.create() に response_format={"type":"json_object"} を追加
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": incident},
        ],
        # EDIT HERE! response_format を追加
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
        print("ヒント: response_format={{\"type\": \"json_object\"}} を追加してください")


# ── メイン ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="module2_prompt.py — プロンプト設計演習")
    parser.add_argument("--step", type=int, default=1, choices=[1, 2, 3, 4],
                        help="実行するステップ (1-4)")
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
