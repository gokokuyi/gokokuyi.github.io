#!/usr/bin/python
# Module 3: RAG — Embeddings 演習ファイル (サンプル/完成版)
from typing import Optional, Sequence

import yaml
from openai import OpenAI

from utils.azure_auth import get_azure_token_provider
from utils.logger import get_logger

logger = get_logger()


def calc_cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """2つの Sequence[float] からコサイン類似度を算出して返す"""
    if len(vec1) != len(vec2):
        raise ValueError(f"2つのベクトルの次元数が一致しません: len(vec1)={len(vec1)}, len(vec2)={len(vec2)}")
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude_vec1 = sum(a**2 for a in vec1) ** 0.5
    magnitude_vec2 = sum(b**2 for b in vec2) ** 0.5
    if magnitude_vec1 == 0 or magnitude_vec2 == 0:
        return 0.0
    return dot_product / (magnitude_vec1 * magnitude_vec2)


def main(inputs: Optional[list[str]], model: str, dimensions: Optional[int]) -> None:
    # inputs が設定されているか判定
    if inputs is None:
        logger.warning("入力が空です。--inputs オプションを使用して入力を指定してください。")
        return

    # config.yaml に格納された設定の読み込み
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # API クライアントの設定
    client_config = config.get("OPENAI_CLIENT", {})
    base_url = client_config.get("BASE_URL")
    if base_url is None:
        raise ValueError("OPENAI_CLIENT の 'BASE_URL' が設定されていません。config.yaml を確認してください。")
    api_key = client_config.get("API_KEY", get_azure_token_provider())
    client = OpenAI(base_url=base_url, api_key=api_key)

    # NOTE: `dimensions` のパラメータに None を指定するとリクエストに失敗してしまう
    #
    #       case: dimensions に None が指定されている場合（= コマンドライン引数で指定しなかった場合）
    #             ... = client.embeddings.create(
    #                       input=inputs,
    #                       model=model,
    #                       dimensions=dimensions,  # ← dimensions に None が代入される
    #                   ) # これはエラーになる
    #
    #             ... = client.embeddings.create(
    #                      input=inputs,
    #                       model=model,
    #                   )  # これはOK
    #
    #            case: dimensions に整数が指定されている場合
    #            ... = client.embeddings.create(
    #                   input=inputs,
    #                   model=model,
    #                   dimensions=dimensions,   # <- dimensions に整数が代入される
    #                   )  # これはOK
    #
    #            ... = client.embeddings.create(
    #                   input=inputs,
    #                   model=model,
    #                   )  # エラーにはならないが、コマンドライン引数で指定した dimensions の値が反映されない
    #
    #       これを回避するために、今回は事前にパラメータを指定するための dict を用意し、
    #       `dimensions` に値が指定されているときだけ dict に dimensions を指定するための値を設定する
    params = {"model": model, "input": inputs}
    if dimensions:
        params["dimensions"] = dimensions

    # NOTE: **params の ** は Python のアンパック機能です。
    #          これにより、{"model": ..., "input": ...} の辞書オブジェクトを、model=..., input=... の形で関数に渡しています

    # Step 1: Embeddings API を呼び出して埋め込み表現を取得する
    embeddings = client.embeddings.create(**params)

    # Step 2: 取得した embeddings オブジェクトを print する
    print(embeddings)
    for i, data in enumerate(embeddings.data):
        print(f"[{i}] model={embeddings.model}, index={data.index}, embedding 次元数={len(data.embedding)}")

    # Step2: コサイン類似度の変化を見てみよう
    if len(inputs) > 1:
        init_i = 0
        for i in range(init_i, len(inputs)):
            for j in range(i + 1, len(inputs)):
                input_i = inputs[i]
                embedding_i = embeddings.data[i].embedding
                input_j = inputs[j]
                embedding_j = embeddings.data[j].embedding
                cosine_similarity = calc_cosine_similarity(embedding_i, embedding_j)
                print(f"「{input_i}」と「{input_j}」のコサイン類似度は、{cosine_similarity:.3f} です。")

    return


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=str, nargs="+")
    parser.add_argument("--model", type=str, default="text-embedding-3-small")
    parser.add_argument("--dimensions", type=int)
    args = parser.parse_args()

    main(**vars(args))
