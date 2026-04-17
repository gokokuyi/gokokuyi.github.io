#!/usr/bin/python
"""
Module 4: ツール利用 — Step 2: 複数ツールの定義 演習ファイル

目標:
    2つ目のツール get_axxx_company_profile をツールリストに登録し、
    function_call ループで正しく処理できるようにする。

実行: python module4_tools-step2.py
"""
import json
import textwrap
from typing import Any, Optional, TypedDict

import yaml
from openai import OpenAI

from utils.rag import calc_cosine_similarity, load_vector_store
from utils.azure_auth import get_azure_token_provider
from utils.logger import get_logger

logger = get_logger()


class RetrievalResult(TypedDict, total=False):
    id: str
    cosine_similarity: float


def search_axxx_group_documents(
    client: OpenAI,
    vector_store: dict[str, Any],
    search_query: str,
    top_k: Optional[int] = None,
) -> list[RetrievalResult]:
    """Axxx Japanグループの社内文書をベクトル検索する"""
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


def get_axxx_company_profile(vector_store: dict[str, Any]) -> list[RetrievalResult]:
    """ベクターストアから Axxx Japan グループの会社概要文書を取得する。
    ファイル名が事前に判明しているため、ベクトル検索を行わず直接フィルタする。
    """
    target_file_name = "jxxx-company-profile.txt"
    results = [RetrievalResult(id=id_) for id_ in vector_store if target_file_name in id_]
    logger.info(f"抽出結果: {[result['id'] for result in results]}")
    return results


def main(search_dir: str = "203_rag-chat", top_k: int = 3, reset: bool = False) -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    client_config = config.get("OPENAI_CLIENT", {})
    base_url = client_config.get("BASE_URL")
    if base_url is None:
        raise ValueError("OPENAI_CLIENT の BASE_URL が設定されていません。config.yaml を確認してください。")
    api_key = client_config.get("API_KEY", get_azure_token_provider())
    client = OpenAI(base_url=base_url, api_key=api_key)

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
    params = {k: v for k, v in params.items() if v}

    vector_store = load_vector_store(search_dir, client, reset)

    tools = [
        {
            "type": "function",
            "name": "search_axxx_group_documents",
            "description": (
                "Axxx Japan グループの社内文書を検索する。"
                "クラウド費用・システム仕様・社内規程・組織情報など、"
                "Axxx Japan 社内の情報が必要な質問に対して使用する。"
                "一般常識・計算・社内文書と無関係な質問には使用しない。"
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "ユーザの質問に回答する情報を検索するための適切なクエリ",
                    }
                },
                "required": ["search_query"],
                "additionalProperties": False,
            },
        },
        # ══════════════════════════════════════════════════════════════════
        # EDIT HERE! get_axxx_company_profile をツールリストに登録してください
        # ヒント: 上の search_axxx_group_documents の定義を参考にする
        #   - name: "get_axxx_company_profile"
        #   - description: 会社概要文書を取得するツール（引数なし）
        #   - parameters: 引数なし → properties={}, required=[]
        # ══════════════════════════════════════════════════════════════════
        {
            # EDIT HERE!
        },
    ]

    messages = []

    instructions = """
    ## 役割
    あなたは Axxx Japan および Axxx Japan グループの各種サービスに関する質問に答える、優秀なアシスタントです。

    ## スキル
    - Axxx Japan グループに関する質問: search_axxx_group_documents でキーワード検索できます
    - Axxx Japan グループの会社概要を知りたい場合: get_axxx_company_profile で取得できます
    - Axxx Japan グループと無関係な質問: ツールを使わず直接回答します

    ## タスク
    ユーザからの質問に対して、必要に応じてツールを使いながら、正確かつわかりやすい回答を提供してください。

    ## 制約
    回答に際しては過去の対話履歴よりも検索結果の情報を優先してください。
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
                    search_query = args["search_query"]
                    search_result = search_axxx_group_documents(client, vector_store, search_query, top_k)
                    retrieved_contents = [vector_store[result["id"]]["content"] for result in search_result]
                    retrieved_contents_block = "\n\n----------\n\n".join(retrieved_contents)
                    logger.debug(retrieved_contents_block)
                    messages.append({
                        "type": "function_call_output",
                        "call_id": output.call_id,
                        "output": retrieved_contents_block,
                    })

                elif output.name == "get_axxx_company_profile":
                    getter_result = get_axxx_company_profile(vector_store)
                    retrieved_contents = [vector_store[result["id"]]["content"] for result in getter_result]
                    retrieved_contents_block = "\n\n----------\n\n".join(retrieved_contents)
                    logger.debug(retrieved_contents_block)
                    messages.append({
                        "type": "function_call_output",
                        "call_id": output.call_id,
                        "output": retrieved_contents_block,
                    })
                else:
                    logger.warning(f"Unknown function {output.name} has been called.")

                if messages[-1].get("type") == "function_call_output":
                    response = client.responses.create(
                        instructions=instructions,
                        input=messages,
                        **params,
                    )
                    messages += response.output
                    print(f"Assistant: {response.output_text}")

    logger.info("Bye")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--search_dir", type=str, default="203_rag-chat")
    parser.add_argument("--top_k", type=int, default=3)
    parser.add_argument("--reset", action="store_true")

    args = parser.parse_args()
    main(**vars(args))
