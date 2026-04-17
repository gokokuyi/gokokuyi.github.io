#!/usr/bin/python
"""
Module 4: ツール利用 — Step 1: Function Calling 基本 演習ファイル

目標:
    1. ツール定義の description に適切な説明文を書く
    2. output.arguments から search_query を取り出す
    3. ツール実行結果を function_call_output 形式で messages に追加する

実行: python module4_tools-step1.py
"""
import json
import textwrap
from typing import Optional, TypedDict

import yaml
from openai import OpenAI

from utils.rag import calc_cosine_similarity, load_vector_store
from utils.azure_auth import get_azure_token_provider
from utils.logger import get_logger

logger = get_logger()


class RetrievalResult(TypedDict, total=False):
    id: str
    cosine_similarity: float


def main(search_dir: str = "203_rag-chat", top_k: int = 3, reset: bool = False) -> None:
    # config.yaml に格納された設定の読み込み
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # API クライアントの設定
    client_config = config.get("OPENAI_CLIENT", {})
    base_url = client_config.get("BASE_URL")
    if base_url is None:
        raise ValueError("OPENAI_CLIENT の BASE_URL が設定されていません。config.yaml を確認してください。")
    api_key = client_config.get("API_KEY", get_azure_token_provider())
    client = OpenAI(base_url=base_url, api_key=api_key)

    # config.yaml からのパラメータ設定（Responses API）
    params_config = client_config.get("PARAMETERS", {})
    params = {
        "model": params_config.get("MODEL", "gpt-4o"),
        "text": {"verbosity": params_config.get("VERBOSITY", "low")},
        "reasoning": {
            "effort": params_config.get("REASONING", {}).get("EFFORT", "low"),
            "summary": params_config.get("REASONING", {}).get("SUMMARY", "auto"),
        },
        "max_output_tokens": params_config.get("MAX_OUTPUT_TOKENS", ""),
    }
    params = {k: v for k, v in params.items() if v}  # 値が空でないパラメータのみを残す

    # 検索対象の埋め込み表現を取得する
    vector_store = load_vector_store(search_dir, client, reset)

    # RAG 検索関数（完成済み）
    def search_axxx_group_documents(search_query: str, top_k: Optional[int] = None) -> list[RetrievalResult]:
        """Axxx Japanグループの社内文書を検索する"""
        embeddings = client.embeddings.create(
            input=search_query,
            model="text-embedding-3-small",
        )
        search_query_embedding = embeddings.data[0].embedding
        retrieval_results = []
        for id_ in vector_store:
            embedding_in_vector_store = vector_store[id_]["embedding"]
            cosine_similarity = calc_cosine_similarity(search_query_embedding, embedding_in_vector_store)
            retrieval_results.append(RetrievalResult(id=id_, cosine_similarity=cosine_similarity))
        top_k_result = sorted(retrieval_results, key=lambda x: x["cosine_similarity"], reverse=True)[:top_k]
        logger.info(f"検索結果 Top {top_k}: {[result['id'] for result in top_k_result]}")
        return top_k_result

    # ══════════════════════════════════════════════════════════════════
    # STEP 1: ツール定義の description を完成させてください
    # LLM はこの説明を読んで「いつこのツールを呼ぶか」を判断します。
    # 以下の3点を含む説明文を書いてください:
    #   - 何の文書を検索するか（Axxx Japan グループの社内文書）
    #   - どんな質問のときに使うか（クラウド費用・システム仕様・社内規程など）
    #   - 使わないケース（社内文書と無関係な一般的質問）
    # ══════════════════════════════════════════════════════════════════
    tools = [
        {
            "type": "function",
            "name": "search_axxx_group_documents",
            "description": "",  # EDIT HERE! (Step 1) 適切な説明文を書いてください
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "ユーザの質問に回答する情報を検索するための適切なクエリ"
                    },
                },
                "required": ["search_query"],
                "additionalProperties": False,
            },
        }
    ]

    messages = []

    instructions = """
    ## 役割
    あなたは Axxx Japan および Axxx Japan グループの各種サービスに関する質問に答える、優秀なアシスタントです。

    ## スキル
    ユーザの質問が Axxx Japan グループの企業に関する場合、関連文書を検索するツールを利用することができます。
    また、ユーザの質問が Axxx Japan グループと関連しない場合、ツールを利用せず迅速に回答することができます。

    ## タスク
    ユーザからの質問に対して、必要に応じて検索結果を参照しながら、正確かつわかりやすい回答を提供してください。

    ## 制約
    回答に際しては対話履歴も参考にして問題ないですが、過去の対話履歴よりも検索結果の情報を優先してください。
    """
    instructions = textwrap.dedent(instructions).strip()
    logger.info("`q` または `quit` で終了")

    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ["q", "quit"]:
            break
        if user_input == "":
            continue

        messages.append({"role": "user", "content": user_input})
        response = client.responses.create(
            instructions=instructions,
            input=messages,
            tools=tools,
            **params,
        )

        messages += response.output
        if response.output_text:
            print(f"Assistant: {response.output_text}")

        for output in response.output:
            if output.type == "function_call":
                logger.info(f"Calling `{output.name}` with `{output.arguments}`!")

                if output.name == "search_axxx_group_documents":
                    args = json.loads(output.arguments)

                    # ══════════════════════════════════════════════════════
                    # STEP 2: args 辞書から search_query を取り出してください
                    # ヒント: args["search_query"] でキーを指定して値を取り出す
                    # ══════════════════════════════════════════════════════
                    search_query = ""  # EDIT HERE! (Step 2)

                    search_result = search_axxx_group_documents(search_query, top_k)
                    retrieved_contents = [vector_store[result["id"]]["content"] for result in search_result]
                    retrieved_contents_block = "\n\n----------\n\n".join(retrieved_contents)
                    logger.debug(retrieved_contents_block)

                    # ══════════════════════════════════════════════════════
                    # STEP 3: ツール実行結果を messages に追加してください
                    # ヒント: messages.append({...}) で以下の辞書を追加する
                    #   "type": "function_call_output"
                    #   "call_id": output.call_id
                    #   "output": retrieved_contents_block
                    # ══════════════════════════════════════════════════════
                    # EDIT HERE! (Step 3)

                    # 検索結果を踏まえて再度応答を生成（tools は渡さない）
                    response = client.responses.create(
                        instructions=instructions,
                        input=messages,
                        **params,
                    )
                    messages += response.output
                    print(f"Assistant: {response.output_text}")
                else:
                    logger.warning(f"Unknown function {output.name} has been called.")

    logger.info("Bye")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="`python module4_tools-step1.py --reset` で起動すると、ベクターストアを再構築します"
    )
    parser.add_argument("--search_dir", type=str, default="203_rag-chat")
    parser.add_argument("--top_k", type=int, default=3)
    parser.add_argument("--reset", action="store_true")

    args = parser.parse_args()
    main(**vars(args))
