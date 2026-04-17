#!/usr/bin/python
"""
Module 4: ツール利用 — Step 3: ツールパラメータの拡張 演習ファイル

目標:
    search_axxx_group_documents ツールに category パラメータを追加し、
    検索対象の FAQ ファイルをカテゴリで絞り込めるようにする。

実行: python module4_tools-step3.py
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

# カテゴリ名とFAQファイル名のマッピング
CATEGORY_TO_FILENAME = {
    "general":    "jxxx-faq-general.txt",
    "systems":    "jxxx-systems-faq.txt",
    "consulting": "jxxx-consulting-faq.txt",
    "data":       "jxxx-data-faq.txt",
    "ai":         "jxxx-ai-dept-faq.txt",
}


class RetrievalResult(TypedDict, total=False):
    id: str
    cosine_similarity: float


def search_axxx_group_documents(
    client: OpenAI,
    vector_store: dict[str, Any],
    search_query: str,
    category: str = "",
    top_k: Optional[int] = None,
) -> list[RetrievalResult]:
    """Axxx Japanグループの社内文書をベクトル検索する。
    category が指定された場合、対応するFAQファイルのみを検索対象とする。
    """
    embeddings = client.embeddings.create(
        input=search_query,
        model="text-embedding-3-small",
    )
    search_query_embedding = embeddings.data[0].embedding

    # カテゴリでファイルを絞り込む（未指定の場合は全ファイルを対象）
    target_filename = CATEGORY_TO_FILENAME.get(category)

    retrieval_results = []
    for id_ in vector_store:
        if target_filename and not id_.startswith(target_filename):
            continue
        embedding_in_vector_store = vector_store[id_]["embedding"]
        cosine_similarity = calc_cosine_similarity(search_query_embedding, embedding_in_vector_store)
        retrieval_results.append(RetrievalResult(id=id_, cosine_similarity=cosine_similarity))

    top_k_result = sorted(retrieval_results, key=lambda x: x["cosine_similarity"], reverse=True)[:top_k]
    logger.info(f"検索結果 Top {top_k} (category={category!r}): {[result['id'] for result in top_k_result]}")
    return top_k_result


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
                    },
                    # ══════════════════════════════════════════════════════════════
                    # EDIT HERE! category パラメータを追加してください
                    # LLM がユーザの質問から適切なカテゴリを推定し、
                    # 検索対象の FAQ ファイルを絞り込むために使います。
                    #
                    # 追加する定義:
                    #   "category": {
                    #       "type": "string",
                    #       "enum": [...],   ← CATEGORY_TO_FILENAME のキーを列挙
                    #       "description": "検索対象のFAQカテゴリ。不明な場合は空文字列。"
                    #   }
                    # ══════════════════════════════════════════════════════════════
                },
                "required": ["search_query"],
                "additionalProperties": False,
            },
        },
    ]

    messages = []

    instructions = """
    ## 役割
    あなたは Axxx Japan および Axxx Japan グループの各種サービスに関する質問に答える、優秀なアシスタントです。

    ## スキル
    ユーザの質問が Axxx Japan グループの企業に関する場合、関連文書を検索するツールを利用することができます。
    また、質問の内容から適切な FAQ カテゴリ（general/systems/consulting/data/ai）を推定して、
    検索対象を絞り込むことができます。

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
                    category = args.get("category", "")
                    search_result = search_axxx_group_documents(client, vector_store, search_query, category, top_k)
                    retrieved_contents = [vector_store[result["id"]]["content"] for result in search_result]
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
