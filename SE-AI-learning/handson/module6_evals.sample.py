"""
Module 6: 評価（Evals）— 解答例ファイル
このファイルはすべての # EDIT HERE! 部分が実装済みです。
学習時に自分の実装と比較するために参照してください。

実行方法:
    python module6_evals.sample.py --step 1   # ルールベース評価（オフライン）
    python module6_evals.sample.py --step 2   # LLM-as-judge（Azure OpenAI 必要）
    python module6_evals.sample.py --step 3   # 回帰テスト（Azure OpenAI 必要）
"""

import argparse
import json
import re
import sys
import yaml
from pathlib import Path


# ── 設定読み込み ──────────────────────────────────────────────────────────────
def load_config():
    """config.yaml を読み込んで返す。"""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("config.yaml が見つかりません。handson/setup.html を参照してセットアップしてください。")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── クライアント初期化 ──────────────────────────────────────────────────────
def get_client(config):
    """Azure OpenAI クライアントとモデル名を返す。"""
    from openai import AzureOpenAI
    from utils.azure_auth import get_azure_token_provider

    token_provider = get_azure_token_provider()
    client = AzureOpenAI(
        azure_endpoint=config["azure_endpoint"],
        azure_ad_token_provider=token_provider,
        api_version=config.get("api_version", "2025-01-01"),
    )
    model = config.get("model", "gpt-4o")
    return client, model


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: ルールベース評価（解答例）
# ═══════════════════════════════════════════════════════════════════════════════

# LLMの出力が満たすべきスキーマ仕様
EXPECTED_SCHEMA = {
    "required_keys": ["summary", "priority", "action_items"],
    "priority_values": ["high", "medium", "low"],
    "action_items_min_count": 1,
}

# テスト用のLLM出力サンプル
SAMPLE_LLM_OUTPUTS = [
    # 正常な出力
    '{"summary": "インシデント要約", "priority": "high", "action_items": ["調査開始", "担当者連絡"]}',
    # 必須キーが不足している出力
    '{"summary": "要約のみ"}',
    # priority の値が不正な出力
    '{"summary": "要約", "priority": "critical", "action_items": ["対応"]}',
    # JSONとして不正な出力
    'これはJSONではありません',
]


def evaluate_json_output(llm_output: str) -> dict:
    """LLMのJSON出力がスキーマを満たすか評価する。

    以下の4つのチェックを行う:
    1. llm_output が有効な JSON かどうか（json.loads でパース）
    2. EXPECTED_SCHEMA の required_keys がすべて存在するか
    3. priority が priority_values のいずれかか
    4. action_items が最低 action_items_min_count 件あるか

    Args:
        llm_output: LLMが生成したJSON形式の文字列

    Returns:
        {"passed": bool, "errors": list[str], "warnings": list[str]} の辞書
    """
    result = {"passed": False, "errors": [], "warnings": []}

    # ✅ 解答: チェック1 — 有効なJSONかどうかを確認する
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError as e:
        result["errors"].append(f"JSONパースエラー: {e}")
        return result

    # ✅ 解答: チェック2 — 必須キーの存在確認
    for key in EXPECTED_SCHEMA["required_keys"]:
        if key not in data:
            result["errors"].append(f"必須キーが存在しない: {key}")

    # ✅ 解答: チェック3 — priority の値が有効か確認する
    if "priority" in data:
        if data["priority"] not in EXPECTED_SCHEMA["priority_values"]:
            result["errors"].append(
                f"priority の値が無効: {data['priority']} "
                f"(有効値: {EXPECTED_SCHEMA['priority_values']})"
            )

    # ✅ 解答: チェック4 — action_items の件数を確認する
    if "action_items" in data:
        min_count = EXPECTED_SCHEMA["action_items_min_count"]
        if len(data["action_items"]) < min_count:
            result["errors"].append(
                f"action_items が最低件数（{min_count}件）を下回っている: "
                f"{len(data['action_items'])}件"
            )

    # すべてのチェックを通過した場合に passed = True にする
    result["passed"] = len(result["errors"]) == 0
    return result


def step1():
    """Step 1: ルールベース評価（JSON スキーマ検証）のデモを実行する。"""
    print("=" * 60)
    print("Step 1: ルールベース評価（JSON スキーマ検証）")
    print("=" * 60)

    for i, output in enumerate(SAMPLE_LLM_OUTPUTS, 1):
        result = evaluate_json_output(output)
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"\n出力 {i}: {output[:60]}...")
        print(f"  結果: {status}")
        if result.get("errors"):
            print(f"  エラー: {result['errors']}")
        if result.get("warnings"):
            print(f"  警告: {result['warnings']}")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: LLM-as-judge（解答例）
# ═══════════════════════════════════════════════════════════════════════════════

# 評価用プロンプトテンプレート（基準・スケール・COTを含む）
JUDGE_PROMPT_TEMPLATE = """
# タスク
以下のAI回答の品質を評価してください。

# 評価基準
- 正確性: 情報が正確か（1-5）
- 簡潔性: 不要な情報がないか（1-5）
- 実用性: ユーザーの問題を解決できるか（1-5）

# スコアの定義
5: 完全に正確で簡潔、ユーザーの問題を完全に解決する
4: ほぼ正確で実用的、軽微な不備がある
3: 部分的に正確、改善の余地がある
2: 不正確または不完全で実用性が低い
1: 完全に不正確または有害な情報を含む

# 質問
{question}

# AI回答
{answer}

# 出力形式（必ずこのJSON形式で返してください。コードブロックは不要です）
{{
  "scores": {{"accuracy": <1-5>, "conciseness": <1-5>, "usefulness": <1-5>}},
  "overall": <1-5>,
  "reason": "<評価の根拠を1-2文で>"
}}
"""


def llm_judge(client, model: str, question: str, answer: str) -> dict:
    """LLM-as-judge で回答品質を採点する。

    JUDGE_PROMPT_TEMPLATE に質問と回答を埋め込み、
    LLM に評価させて JSON 形式のスコアを返す。

    Args:
        client: Azure OpenAI クライアント
        model: モデル名
        question: ユーザーの質問文字列
        answer: 評価対象のAI回答文字列

    Returns:
        {"scores": {...}, "overall": int, "reason": str} の辞書
        エラーの場合は空辞書 {}
    """
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(question=question, answer=answer)

    try:
        # ✅ 解答: LLM-as-judge プロンプトを input として送信する
        response = client.responses.create(model=model, input=judge_prompt)
        text = response.output_text

        # コードブロック（```json ... ```）で囲まれている場合に JSON 部分だけ抽出する
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        print(f"llm_judge エラー: {e}")
        return {}


def step2(config):
    """Step 2: LLM-as-judge 評価のデモを実行する。"""
    print("=" * 60)
    print("Step 2: LLM-as-judge 評価")
    print("=" * 60)

    client, model = get_client(config)

    # 品質の異なる2つの回答を評価する
    test_cases = [
        {
            "question": "有給休暇の申請方法を教えてください",
            "answer": "有給休暇はワークフローシステムから申請できます。上司承認後、翌営業日から有効です。",
        },
        {
            "question": "有給休暇の申請方法を教えてください",
            "answer": "休暇は大切です。様々な種類の休暇があり、それぞれに特徴があります。",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i} ---")
        print(f"Q: {case['question']}")
        print(f"A: {case['answer']}")
        result = llm_judge(client, model, case["question"], case["answer"])
        if result:
            print(f"スコア: {result.get('scores', {})} | 総合: {result.get('overall', 'N/A')}")
            print(f"根拠: {result.get('reason', '')}")
        else:
            print("評価結果を取得できませんでした")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: 回帰テスト（解答例）
# ═══════════════════════════════════════════════════════════════════════════════

# 評価用ゴールデンデータセット
GOLDEN_DATASET = [
    {
        "id": "T001",
        "question": "有給休暇は年間何日ですか？",
        "expected_keywords": ["20日", "有給"],
        "min_score": 3,
    },
    {
        "id": "T002",
        "question": "テレワークの申請はどうすればいいですか？",
        "expected_keywords": ["申請", "システム"],
        "min_score": 3,
    },
    {
        "id": "T003",
        "question": "経費精算の締め日はいつですか？",
        "expected_keywords": ["締め日", "月末", "精算"],
        "min_score": 3,
    },
]


def run_regression_test(client, model: str) -> dict:
    """ゴールデンデータセットに対して回帰テストを実行する。

    各テストケースについて:
    1. LLM に質問へ回答させる
    2. expected_keywords が回答に含まれているか確認する
    3. 含まれていれば passed、なければ failed とカウントする
    4. 詳細結果を details リストに追加する

    Args:
        client: Azure OpenAI クライアント
        model: モデル名

    Returns:
        {"total": int, "passed": int, "failed": int, "details": list} の辞書
    """
    results = {
        "total": len(GOLDEN_DATASET),
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    for case in GOLDEN_DATASET:
        try:
            # ✅ 解答1: LLMに質問へ回答させる
            response = client.responses.create(model=model, input=case["question"])
            answer = response.output_text

            # ✅ 解答2: 期待キーワードが回答に含まれるか確認する
            passed = all(kw in answer for kw in case["expected_keywords"])

            # ✅ 解答3: passed / failed をカウントする
            results["passed" if passed else "failed"] += 1

            # ✅ 解答4: 詳細結果を追加する
            results["details"].append({
                "id": case["id"],
                "question": case["question"],
                "passed": passed,
                "expected_keywords": case["expected_keywords"],
                "answer_preview": answer[:80],  # デバッグ用に回答の先頭を保存する
            })

        except Exception as e:
            # エラーが発生した場合は FAIL として記録する
            results["failed"] += 1
            results["details"].append({
                "id": case["id"],
                "question": case["question"],
                "passed": False,
                "expected_keywords": case["expected_keywords"],
                "error": str(e),
            })

    return results


def step3(config):
    """Step 3: 回帰テストのデモを実行する。"""
    print("=" * 60)
    print("Step 3: 回帰テスト")
    print("=" * 60)

    client, model = get_client(config)
    results = run_regression_test(client, model)

    print(f"\n総テスト数: {results['total']}")
    print(f"✅ PASS: {results['passed']}")
    print(f"❌ FAIL: {results['failed']}")

    if results["total"] > 0:
        pass_rate = round(results["passed"] / results["total"] * 100)
        print(f"合格率: {pass_rate}%")
        if pass_rate >= 80:
            print("👍 合格率80%以上をクリアしました！")
        else:
            print("📚 合格率80%未満です。回答に含まれるキーワードを確認してみましょう。")

    for detail in results.get("details", []):
        status = "✅" if detail.get("passed") else "❌"
        print(f"\n{status} {detail.get('id')}: {detail.get('question', '')[:50]}")
        if not detail.get("passed"):
            print(f"   期待キーワード: {detail.get('expected_keywords')}")
            if "answer_preview" in detail:
                print(f"   実際の回答（先頭80文字）: {detail['answer_preview']}")
            if "error" in detail:
                print(f"   エラー: {detail['error']}")


# ── メイン ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Module 6: 評価（Evals）演習（解答例）"
    )
    parser.add_argument(
        "--step",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="実行するステップ番号（1: ルールベース評価 / 2: LLM-as-judge / 3: 回帰テスト）",
    )
    args = parser.parse_args()

    # Step 2・3 は Azure OpenAI 接続が必要
    config = None
    if args.step in [2, 3]:
        config = load_config()

    if args.step == 1:
        step1()
    elif args.step == 2:
        step2(config)
    elif args.step == 3:
        step3(config)
