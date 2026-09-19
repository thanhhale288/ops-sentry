from __future__ import annotations

from typing import Any

from app.rag.embed import tokenize

_CHUNKS: list[dict[str, Any]] = []
_BM25: Any = None
_BUILT = False


def reset() -> None:
    global _CHUNKS, _BM25, _BUILT
    _CHUNKS = []
    _BM25 = None
    _BUILT = False


def ready() -> bool:
    return _BUILT


def build(chunks: list[dict[str, Any]]) -> None:
    global _CHUNKS, _BM25, _BUILT
    reset()
    _CHUNKS = list(chunks)
    _BUILT = True
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return
    corpus = [tokenize(chunk.get("text") or "") for chunk in _CHUNKS]
    if not corpus:
        return
    _BM25 = BM25Okapi(corpus)


def search(query: str, limit: int) -> list[dict[str, Any]]:
    if _BM25 is None or not _CHUNKS or limit <= 0:
        return []
    tokens = tokenize(query)
    if not tokens:
        return []
    scores = _BM25.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    out: list[dict[str, Any]] = []
    for idx, score in ranked:
        if score <= 0:
            break
        chunk = _CHUNKS[idx]
        out.append(
            {
                "id": chunk["id"],
                "doc_id": chunk["doc_id"],
                "title": chunk["title"],
                "text": chunk["text"],
                "score": float(score),
            }
        )
        if len(out) >= limit:
            break
    return out
