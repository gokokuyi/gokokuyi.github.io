"""
共通 RAG ユーティリティ
calc_cosine_similarity と load_vector_store を module3/module4 で共有するために切り出したモジュール。
"""
import json
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from openai import BadRequestError, OpenAI

from utils.logger import get_logger

logger = get_logger()


def calc_cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """2つの Sequence[float] からコサイン類似度を算出して返す"""
    if len(vec1) != len(vec2):
        raise ValueError(f"2つのベクトルの次元数が一致しません: len(vec1)={len(vec1)}, len(vec2)={len(vec2)}")
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude_vec1 = sum(a ** 2 for a in vec1) ** 0.5
    magnitude_vec2 = sum(b ** 2 for b in vec2) ** 0.5
    if magnitude_vec1 == 0 or magnitude_vec2 == 0:
        return 0.0
    return dot_product / (magnitude_vec1 * magnitude_vec2)


def load_vector_store(search_dir: str, client: OpenAI, reset: bool) -> dict[str, Any]:
    """search_dir 内の .txt ファイルをベクトル化し、辞書形式で返す。
    キャッシュ（vector_store.json）が存在する場合はそちらを優先して読み込む。
    reset=True の場合はキャッシュを無視して再取得する。
    """
    def _load_cache(path_to_vector_store: Path) -> Optional[dict[str, Any]]:
        try:
            with open(path_to_vector_store, mode="r", encoding="utf-8") as f:
                vector_store = json.load(f)
            logger.info("埋め込み表現をキャッシュから読み込みました")
            return vector_store
        except json.JSONDecodeError:
            logger.warning(f"{path_to_vector_store} の読み込みに失敗しました。キャッシュを破棄します。")
            return None
        except Exception as e:
            logger.error(f"エラー '{e}' が発生しました。キャッシュを破棄し、埋め込み表現を再取得します。")
            return None

    def _load_resources(text_files: Iterable[Path]) -> list[dict[str, str]]:
        resources = []
        for file in text_files:
            with open(file, mode="r", encoding="utf-8") as f:
                content = f.read()
            resources.append({"id": file.name, "content": content})
        return resources

    def _save_cache(path_to_vector_store: Path, vector_store: dict[str, Any]) -> None:
        with open(path_to_vector_store, mode="w", encoding="utf-8") as f:
            json.dump(vector_store, f, ensure_ascii=False, indent=4)
        logger.info("埋め込み表現をキャッシュに保存しました")

    path_to_vector_store = Path(search_dir).joinpath("vector_store.json")
    use_cache = path_to_vector_store.exists() and reset is False
    if use_cache:
        vector_store = _load_cache(path_to_vector_store)
        if vector_store:
            return vector_store

    text_files = Path(search_dir).glob("*.txt")
    resources = _load_resources(text_files)
    vector_store = {}
    for resource in resources:
        id_ = resource["id"]
        content = resource["content"]
        try:
            response = client.embeddings.create(
                input=content,
                model="text-embedding-3-small",
            )
            embedding = response.data[0].embedding
            vector_store[id_] = {"content": content, "embedding": embedding}
        except BadRequestError as e:
            logger.error(e)
        except Exception as e:
            logger.error(f"埋め込み表現の取得中に予期せぬエラーが発生しました。エラー: {e}")

    if not vector_store:
        raise ValueError(f"ベクターストアの構築に失敗しました。'{search_dir}' に .txt ファイルがあるか確認してください。")

    _save_cache(path_to_vector_store, vector_store)
    return vector_store
