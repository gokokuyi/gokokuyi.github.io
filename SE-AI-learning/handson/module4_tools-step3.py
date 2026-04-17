#!/usr/bin/python
import json
import textwrap
from typing import Any, Optional, TypedDict

import yaml
from openai import OpenAI

from utils._204 import calc_cosine_similarity, initial_setup, load_vector_store
from utils.azure_auth import get_azure_token_provider
from utils.logger import get_logger

logger = get_logger()


class RetrievalResult(TypedDict, total=False):
    id: str
    cosine_similarity: float


def search_sxxx_group_documents(
    client: OpenAI,
    vector_store: dict[str, Any],
    search_query: str,
    company_names: list[str],
    top_k: Optional[int] = None,
) -> list[RetrievalResult]:
    """SXXXグループに関する文書を検索する関数。

    引数に与えられた search_query の埋め込み表現を取得し、ベクターストアとして保持されているSxxxグループに関する文書の
    埋め込め表現とのコサイン類似度を求め、その値の降順 top_k 件の id とコサイン類似度を返却する。

    Args:
        client (OpenAI) : OpenAI API クライアント
        vector_store (dict[str, Any]) : 検索対象のベクターストア
        search_query (str): 検索クエリ
        company_names (list[str]): LLMによって推定されたユーザーの質問と関連する企業名のリスト
        top_k (int | None): 抽出する検索結果の件数。None の場合は全件返す。

    Returns:
        list[RetrievalResult]: 抽出されたレコードの id とコサイン類似度が記録された辞書型のリスト
    """
    # Retriever：密ベクトル検索を用いた類似文章の検索
    # ユーザ入力の埋め込み表現を取得
    embeddings = client.embeddings.create(
        input=search_query,
        model="text-embedding-3-small",
    )
    search_query_embedding = embeddings.data[0].embedding

    # 企業名と、各企業に関するファイル名のリストの辞書
    known_company_to_filename = {
        "日xxxxx究所": ["jxx-company-profile.txt"],
        "三xxxxx銀行": ["sxxx_wikipedia.txt", "sxxx-faq-id8384.txt"],
        "三xxxxxカード": ["sxxx-faq-id93.txt"],
        "Sxxx日x証券": ["sxxxnixxxfaq-id021.txt"],
        "Sxxxコンシューマーファイナンス": ["sxxxcf-faq-sample.txt"],
    }

    # 指定された企業のファイル名を取得。指定がない（または合致しない）場合は全てのファイル名を対象とする
    target_filenames = []
    for company_name in company_names:
        target_filenames.extend(known_company_to_filename.get(company_name, []))
    if not target_filenames:
        for filenames in known_company_to_filename.values():
            target_filenames.extend(filenames)
    # startwith() で一括判定させるために tuple へ変換
    target_filenames_tuple = tuple(target_filenames)

    # vector_store 内の全ての埋め込み表現とのコサイン類似度を計算し、類似度の高い順に top_k を retrieval_result として保持
    retrieval_results = []
    for id_ in vector_store:
        is_target_file = id_.startswith(target_filenames_tuple)  # startwith と tuple を使った複数文字列を条件として判定
        if not is_target_file:
            continue
        embedding_in_vector_store = vector_store[id_]["embedding"]
        # コサイン類似度の計算
        cosine_similarity = calc_cosine_similarity(search_query_embedding, embedding_in_vector_store)
        retrieval_results.append(RetrievalResult(id=id_, cosine_similarity=cosine_similarity))
    # コサイン類似度について降順に top_k 件の検索結果を return
    top_k_result = sorted(retrieval_results, key=lambda x: x["cosine_similarity"], reverse=True)[:top_k]
    logger.info(f"検索結果 Top {top_k}: {[result['id'] for result in top_k_result]}")
    return top_k_result


def main(search_dir: str = "module4_tools", top_k: int = 3, reset: bool = False) -> None:
    # 初回起動時に 203_rag-chat で利用したリソースを再利用する準備をする
    initial_setup(search_dir)

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
    params = {k: v for k, v in params.items() if v} # 値が空でないパラメータのみを残す

    # 検索対象の埋め込み表現を取得する
    vector_store = load_vector_store(search_dir, client, reset)

    # LLMに渡すツールのリスト
    tools = [
        {
            "type": "function",
            "name": "search_sxxx_group_documents",
            "description": "三ｘｘｘグループ各社に関連する文書を検索する関数",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "ユーザの質問に回答する情報を検索するための適切なクエリ",
                    },
                    # EDIT HERE: LLM にユーザの質問で具体的に言及・意図されているSxxxグループ企業の名称をリスト型で推定させて、検索時のファイルとして利用できるようにしょうましょう,
                },
                "required": ["search_query"],
                "additionalProperties": False,
            },
        },
    ]

    # 対話履歴の読み込み処理は本ハンズオンでは省略
    messages = []

    # チャットの実装
    instructions = """
    ## 役割
    あなたは Sxxx および Sxxx グループの各種サービスに関する質問に答える、優秀なアシスタントです。

    ## スキル
    ユーザの質問が Sxxx グループの企業に関する場合、関連文書を検索するツールを利用することができます。
    また、ユーザの質問が Sxxx グループの企業と関連しない場合、ツールを利用せず迅速に回答することができます。

    ## タスク
    ユーザからの質問に対して、必要に応じて検索結果を参照しながら、正確かつわかりやすい回答を提供してください。

    ## 制約
    回答に際しては対話履歴も参考にして問題ないですが、過去の対話履歴よりも検索結果の情報を優先してください。
    """
    instructions = textwrap.dedent(instructions).strip()
    logger.info("`q` または `quit` で終了")

    while True:
        # ユーザー入力
        user_input = input("User: ").strip()

        if user_input.lower() in ["q", "quit"]:
            break
        if user_input == "":
            continue

        # ユーザの入力を messages に追加し、Responses API にリクエスト
        messages.append({"role": "user", "content": user_input})
        response = client.responses.create(
            instructions=instructions,
            input=messages,
            tools=tools,
            **params,
        )

        # LLM の応答を格納しつつ、テキスト応答があれば ClI に表示
        messages += response.output
        if response.output_text:
            print(f"Assistant: {response.output_text}")

        # LLM の応答に `function_call` が含まれていればツールを実行し、再度 LLM を呼び出す
        for output in response.output:
            if output.type == "function_call":
                logger.info(f"Calling `{output.name}` with `{output.arguments}`!")

                # `output.name` が `search_sxxx_group_documents` であれば関数を呼び出す
                if output.name == "search_sxxx_group_documents":
                    # ツール実行に必要な引数を取り出し、適切な型（今回は str）に変換する
                    args = json.loads(output.arguments)
                    search_query = args.get("search_query", user_input)  # user_input をフォールバック用に設定
                    company_names = args.get("company_names", [])
                    search_result = search_sxxx_group_documents(client, vector_store, search_query, company_names, top_k)
                    # 検索結果に含まれるテキストを文字列として展開
                    retrieved_contents = [vector_store[result["id"]]["content"] for result in search_result]  # 内包表記
                    retrieved_contents_block = "\n\n----------\n\n".join(
                        retrieved_contents
                    )  # コンテンツのリストを区切り文字列で結合
                    logger.debug(retrieved_contents_block)
                    # ツールの実行結果として `retrieved_contents_block` を `messages` に格納する
                    messages.append(
                        {
                            "type": "function_call_output",
                            "call_id": output.call_id,
                            "output": retrieved_contents_block,
                        }
                    )
                else:
                    logger.warning(f"Unknown function {output.name} has been called.")

                # messages[-1] の type が `function_call_output` であれば、ツールの実行結果を踏まえて応答を再生成
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

    # Module 4: ツール利用 の設定
    parser.add_argument("--search_dir", type=str, default="module4_tools")
    parser.add_argument("--top_k", type=int, default=3)
    parser.add_argument("--reset", action="store_true")

    args = parser.parse_args()
    main(**vars(args))
