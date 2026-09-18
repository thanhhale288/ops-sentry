from __future__ import annotations

from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import settings
from app.rag.embed import embed
from app.rag.ids import stable_id

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sops"

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
                return count
            qdrant.delete_collection(settings.collection)
    except Exception:
        exists = False

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
    return len(points)


def retrieve(query: str, k: int | None = None) -> list[dict[str, Any]]:
    k = k or settings.retrieve_k
    qdrant = get_client()
    ingest()
    hits = qdrant.query_points(
        collection_name=settings.collection,
        query=embed(query, settings.embed_dim),
        limit=k,
        with_payload=True,
    ).points
    out: list[dict[str, Any]] = []
    for hit in hits:
        payload = hit.payload or {}
        out.append(
            {
                "doc_id": payload.get("doc_id", ""),
                "title": payload.get("title", ""),
                "text": payload.get("text", ""),
                "score": float(hit.score or 0.0),
            }
        )
    return out
