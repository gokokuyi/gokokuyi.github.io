#!/usr/bin/python
import json
import textwrap

import yaml
from openai import OpenAI

from utils.azure_auth import get_azure_token_provider


def main(verbose: bool = False) -> None:
    # config.yaml に格納された設定の読み込み
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # API クライアントの設定
    client_config = config.get("OPENAI_CLIENT", {})
    base_url = client_config.get("BASE_URL")
    if base_url is None:
        raise ValueError("`OPENAI_CLIENT` の `BASE_URL` が設定されていません。config.yaml を確認してください。")
    api_key = client_config.get("API_KEY", get_azure_token_provider())
    client = OpenAI(base_url=base_url, api_key=api_key)

    # `config.yaml` からのパラメータ設定（Responses API）
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
    params = {k: v for k, v in params.items() if v}  # 値が空でないパラメータのみを残す

    # ツールの定義
    def first_tool(lang_code: str) -> None:
        if lang_code == "ja":
            print("これは最初のツールです！")
        elif lang_code == "zh":
            print("这是我的第一个工具！")
        elif lang_code == "ko":
            print("이것은 나의 첫 번째 도구입니다!")
        else:
            print("This is my first tool!")

    # LLMに渡すツールのリスト
    tools = [
        {
            "type": "function",
            "name": "first_tool",
            "description": "Function tool のためのモック関数。メッセージを表示するため、ユーザの入力内容に関わらず実行される。",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "lang_code": {
                        "type": "string",
                        "description": "ユーザの入力に対応する言語の ISO-639 コード（例: 'en', 'ja'）",
                    }
                },
                "required": ["lang_code"],
                "additionalProperties": False,
            },
        }
    ]

    # LLMに対する指示
    instructions = """
        ユーザの入力テキストの言語に応じて、`first_tool` を呼び出してください。
        ただし、`q` もしくは `quit` と入力された場合は、first_tool を呼び出さずに対話を終了してください。
    """
    instructions = textwrap.dedent(instructions).strip()

    # 入力するメッセージ
    user_input = input("User: ").strip()
    if user_input == "":
        exit(0)
    response = client.responses.create(
        instructions=instructions,
        input=user_input,
        tools=tools,
        **params,
    )

    # verbose指定時にはレスポンスオブジェクトをJSON形式で表示
    if verbose:
        print(response.model_dump_json(indent=4))

    # レスポンスの内容を確認し、ツール呼び出しがあれば実行
    for output in response.output:
        if output.type == "function_call":
            tool_name = output.name  # "first_tool"
            tool_args_str = output.arguments
            tool_args = json.loads(tool_args_str)  # 文字列型を扱いやすい辞書型に変換
            if tool_name == "first_tool":
                lang_code = tool_args.get("lang_code", "en")
                print(f"`{lang_code}` for first_tool: {lang_code}")
                first_tool(lang_code)
            else:
                print(f"Unknown tool `{tool_name}` was called.")

    if "function_call" not in [output.type for output in response.output]:
        print("No tool was called.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="`python module4_tools-step0.py --verbose` で起動すると、レスポンスの内容を表示できます"
    )
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    main(**vars(args))
