#!/usr/bin/python
# Module 3: RAG — Embeddings 演習ファイル
import json
import textwrap
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import yaml
from openai import BadRequestError, OpenAI

from utils.azure_auth import get_azure_token_provider
from utils.logger import get_logger
from utils.spinner import spinner

logger = get_logger()


def calc_cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """２つの Sequence[float] からコサイン類似度を算出して返す"""
    if len(vec1) != len(vec2):
        raise ValueError(f"２つのベクトルの次元数が一致しません：len(vec1)={len(vec1)}, len(vec2)={len(vec2)}")
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude_vec1 = sum(a**2 for a in vec1) ** 0.5
    magnitude_vec2 = sum(a**2 for a in vec2) ** 0.5
    if magnitude_vec1 == 0 or magnitude_vec2 == 0:
        return 0.0
    return dot_product / (magnitude_vec1 * magnitude_vec2)


def load_vector_store(search_dir: str, client: OpenAI, reset: bool) -> dict[str, Any]:
    def _load_cache(path_to_vector_store: Path) -> Optional[dict[str, Any]]:
        try:
            with open(path_to_vector_store, mode='r', encoding="utf-8") as f:
                vector_store = json.load(f)
            logger.info("埋め込み表現をキャッシュから読み込みました")
            return vector_store

        except json.JSONDecodeError:
            logger.warning(f"{path_to_vector_store}の読み込みに失敗しました。キャッシュを破棄し、埋め込み表現を再取得します。")
            vector_store = None

        except Exception as e:
            logger.error(f"エラー'{e}' が発生しました。キャッシュを破棄し、埋め込み表現を再取得します。")
            vector_store = None

    def _load_resources(text_files: Iterable[Path]) -> list[dict[str, str]]:
        resources = []
        for file in text_files:
            with open(file, mode='r', encoding="utf-8") as f:
                content = f.read()
            resources.append({"id": file.name, "content": content})

        return resources

    def _save_cache(path_to_vector_store: Path, vector_store: dict[str, Any]):
        with open(path_to_vector_store, mode='w', encoding="utf-8") as f:
            json.dump(vector_store, f, ensure_ascii=False, indent=4)
        logger.info("埋め込み表現をキャッシュに保存しました")

    path_to_vector_store = Path(search_dir).joinpath("vector_store.json")
    use_cache = path_to_vector_store.exists() and  reset is False
    if use_cache:
        vector_store = _load_cache(path_to_vector_store)
        if vector_store:
            return vector_store

    # 埋め込み表現の（再）取得と、ベクターストアの構築
    text_files = Path(search_dir).glob("*.txt")
    resources = _load_resources(text_files)
    vector_store = {}
    for resource in resources:
        id_ = resource["id"]
        content = resource["content"]
        try:
            # 埋め込み表現を取得
            response = client.embeddings.create(
                input=content,
                model="text-embedding-3-small"
            )
            embedding = response.data[0].embedding
            vector_store[id_] = {"content": content, "embedding": embedding}
        except BadRequestError as e:
            logger.error(e)
        except Exception as e:
            logger.error(f"埋め込み表現の取得中に予期せぬエラーが発生しました。エラー：{e}")
    if vector_store == {}:
        raise ValueError("ベクターストアの構築に失敗しました。")

    # キャッシュとしてベクターストアを保存し、return する
    _save_cache(path_to_vector_store, vector_store)
    return vector_store


def main(search_dir: str = "module3_rag-chat", top_k: int = 3, reset: bool = False) -> None:
    # config.yaml に格納された設定の読み込み
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # API クライアントの設定
    client_config = config.get("OPENAI_CLIENT", {})
    base_url = client_config.get("BASE_URL")
    if base_url is None:
        raise ValueError("'OPENAI_CLIENT' の 'BASE_URL' が設定されていません。config.yaml を確認してください。")
    api_key = client_config.get("API_KEY", get_azure_token_provider())
    client = OpenAI(base_url=base_url, api_key=api_key)

    # 'config.yaml' からのパラメータ設定（Responses API）
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

    # 対話履歴の読み込み
    messages = []
    path_to_chatlog = Path("module3_rag-chat/chatlog.jsonl")
    if path_to_chatlog.exists() and reset is False:
        try:
            with open(path_to_chatlog, mode="r", encoding="utf-8") as f:
                messages = [json.loads(line) for line in f.read().splitlines()]
        except json.JSONDecodeError:
            logger.warning(f"{path_to_chatlog} の内容を読み込めませんでした。新しい対話履歴を作成します。")
        except Exception as e:
            logger.error(f"{path_to_chatlog} の内容を読み込む際にエラー '{e}' が発生しました。新しい対話履歴を作成します。")

    # チャットの実装
    instructions = """
        ## 役割
        あなたは Axxx Japan および Axxx Japan グループの各種サービスに関する質問に答える、優秀なアシスタントです。

        ## タスク
        ユーザーからの質問に対して、必要に応じて検索結果を参照しながら、正確かつわかりやすい回答を提供してください。

        ## 制約
        回答に際しては対話履歴も参考にして問題ないですが、過去の対話履歴よりも検索結果の情報を優先してください。
    """
    instructions = textwrap.dedent(instructions).strip() # インデントと、前後の改行文字を削除
    logger.info("# 'q' または 'quit' で終了")

    while True:
        # ユーザー入力
        user_input = input("User:").strip()

        if user_input.lower() in ["q", "quit"]:
            break
        if user_input == "":
            continue

        # Retriever:密ベクトル検索を用いた類似文章の検索
        # ユーザー入力の埋め込み表現を取得
        embeddings_api_response = client.embeddings.create(
            input=user_input,
            model="text-embedding-3-small",
        )
        user_input_embedding = embeddings_api_response.data[0].embedding

        # vector_store 内の全ての埋め込み表現とのコサイン類似度を計算し、類似度の高い順に top_k 件を retrieval_result として保持
        retrieval_result = []
        for id_ in vector_store:
            logger.info(f"'{id_}' を検索...　")
            embedding_in_vector_store = vector_store[id_]["embedding"]
            # コサイン類似度の計算
            cosine_similarity = calc_cosine_similarity(user_input_embedding, embedding_in_vector_store)
            retrieval_result.append({"cosine_similarity": cosine_similarity, "id": id_})
        # コサイン類似度について降順に top_k 件の検索結果を保持
        top_k_result = sorted(retrieval_result, key=lambda x: x["cosine_similarity"], reverse=True)[:top_k]
        logger.info(f"検索結果（top {top_k}）: {[result['id'] for result in top_k_result]}")

        # 検索結果に含まれるテキストを文字列として展開
        contents = [vector_store[result["id"]]["content"] for result in top_k_result] # 内包表記でコンテンツを展開（top_k でフィルタ済み）
        contents_block = "\n\n-------------\n\n".join(contents) # コンテンツのリストを区切り文字列で結合
        logger.debug(contents_block)

        # Generator: ユーザー入力と Retriever の検索結果をプロンプトとしてテキストを生成
        user_input_with_contexts = """
            ## 検索結果
            {contents_block}

            ## ユーザー入力
            {user_input}
        """
        user_input_with_contexts = textwrap.dedent(user_input_with_contexts).strip()
        user_input_with_contexts = user_input_with_contexts.format(
            contents_block = contents_block,
            user_input = user_input,
        ) # プレースホルダに値を埋め込む

        # ユーザー入力と検索結果を API に渡してレスポンスを取得し、応答結果を print しつつ messages に格納
        messages = messages + [{"type": "message", "role": "user", "content": user_input_with_contexts}]
        responses_api_response = spinner(client.responses.create)(
            instructions=instructions,
            input=messages,
            **params,
        )
        print(f"Assistant: {responses_api_response.output_text}")
        messages.append({"type": "message", "role": "assistant", "content": responses_api_response.output_text})

    # 対話履歴の保存
    with open(path_to_chatlog, mode="w", encoding="utf-8") as f:
        for message in messages:
            f.write(f"{json.dumps(message, ensure_ascii=False)}\n")

    logger.info("Bye")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="`python module3_rag-chat.py --reset` で起動すると、対話履歴をリセットできます")

    # Module 3 RAG チャットの設定
    parser.add_argument("--search_dir", type=str, default="module3_rag-chat")
    parser.add_argument("--top_k", type=int, default=3)
    parser.add_argument("--reset", action="store_true")

    args = parser.parse_args()
    main(**vars(args))
