from __future__ import annotations

from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import settings
from app.rag import bm25 as bm25_index
from app.rag.embed import embed
from app.rag.ids import stable_id

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sops"
DENSE_MIN = 8
RRF_K = 60
# BM25 is weighted slightly above dense so lexical goldset queries survive hashing-embed noise.
BM25_RRF_WEIGHT = 1.5
DENSE_RRF_WEIGHT = 1.0

_CLIENT: QdrantClient | None = None


def client() -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url, timeout=10)
    return QdrantClient(":memory:")


def get_client() -> QdrantClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = client()
    return _CLIENT


def reset_client() -> None:
    global _CLIENT
    _CLIENT = None
    bm25_index.reset()


def _chunks() -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("-", " ").title()
        doc_id = path.stem
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        heading = title
        for i, para in enumerate(paragraphs):
            if para.startswith("#"):
                heading = para.lstrip("# ").strip() or heading
                continue
            points.append(
                {
                    "id": stable_id(f"{doc_id}:{i}"),
                    "doc_id": doc_id,
                    "title": heading,
                    "text": f"{heading}. {para}",
                }
            )
    return points


def ingest(force: bool = False) -> int:
    qdrant = get_client()
    dim = settings.embed_dim
    exists = False
    try:
        exists = qdrant.collection_exists(settings.collection)
        if exists:
            info = qdrant.get_collection(settings.collection)
            count = int(info.points_count or 0)
            if count > 0 and not force:
                if not bm25_index.ready():
                    bm25_index.build(_chunks())
                return count
            qdrant.delete_collection(settings.collection)
    except Exception:
        exists = False

    if force:
        bm25_index.reset()

    qdrant.create_collection(
        collection_name=settings.collection,
        vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
    )
    raw = _chunks()
    points = [
        qm.PointStruct(
            id=item["id"],
            vector=embed(item["text"], dim),
            payload={"doc_id": item["doc_id"], "title": item["title"], "text": item["text"]},
        )
        for item in raw
    ]
    qdrant.upsert(collection_name=settings.collection, points=points)
    bm25_index.build(raw)
    return len(points)


def _hit_dict(payload: dict[str, Any], score: float) -> dict[str, Any]:
    return {
        "doc_id": payload.get("doc_id", ""),
        "title": payload.get("title", ""),
        "text": payload.get("text", ""),
        "score": score,
    }


def _rrf(rank_lists: list[list[Any]], weights: list[float], k_rrf: int = RRF_K) -> list[tuple[Any, float]]:
    scores: dict[Any, float] = {}
    for ranked, weight in zip(rank_lists, weights):
        for rank, cid in enumerate(ranked, start=1):
            scores[cid] = scores.get(cid, 0.0) + weight / (k_rrf + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def retrieve(query: str, k: int | None = None) -> list[dict[str, Any]]:
    k = k or settings.retrieve_k
    qdrant = get_client()
    ingest()
    dense_limit = max(k, DENSE_MIN)
    hits = qdrant.query_points(
        collection_name=settings.collection,
        query=embed(query, settings.embed_dim),
        limit=dense_limit,
        with_payload=True,
    ).points

    by_id: dict[Any, dict[str, Any]] = {}
    dense_rank: list[Any] = []
    dense_out: list[dict[str, Any]] = []
    for hit in hits:
        payload = hit.payload or {}
        item = _hit_dict(payload, float(hit.score or 0.0))
        dense_out.append(item)
        by_id[hit.id] = item
        dense_rank.append(hit.id)

    bm25_hits = bm25_index.search(query, limit=dense_limit)
    if not bm25_hits:
        return dense_out[:k]

    bm25_rank: list[Any] = []
    for hit in bm25_hits:
        cid = hit["id"]
        bm25_rank.append(cid)
        if cid not in by_id:
            by_id[cid] = _hit_dict(hit, float(hit["score"]))

    fused = _rrf(
        [dense_rank, bm25_rank],
        [DENSE_RRF_WEIGHT, BM25_RRF_WEIGHT],
    )
    out: list[dict[str, Any]] = []
    for cid, score in fused[:k]:
        item = dict(by_id[cid])
        item["score"] = score
        out.append(item)
    return out
