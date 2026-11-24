"""Pluggable embedders. Local ONNX models via fastembed: zero API cost, runs on a laptop CPU."""
from functools import lru_cache
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    name: str
    dim: int
    def passages(self, texts: list[str]) -> list[np.ndarray]: ...
    def query(self, text: str) -> np.ndarray: ...


class FastEmbed:
    def __init__(self, name: str, model: str, dim: int):
        self.name, self.model_name, self.dim = name, model, dim

    @property
    def _model(self):
        return _load(self.model_name)

    def passages(self, texts: list[str]) -> list[np.ndarray]:
        return list(self._model.passage_embed(texts))

    def query(self, text: str) -> np.ndarray:
        # bge models expect a retrieval instruction on the query side; query_embed adds it.
        return next(iter(self._model.query_embed([text])))


@lru_cache(maxsize=4)
def _load(model: str):
    from fastembed import TextEmbedding
    return TextEmbedding(model)


EMBEDDERS: dict[str, Embedder] = {
    "bge-small": FastEmbed("bge-small", "BAAI/bge-small-en-v1.5", 384),
    "bge-base": FastEmbed("bge-base", "BAAI/bge-base-en-v1.5", 768),
}
