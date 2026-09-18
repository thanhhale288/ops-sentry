from __future__ import annotations

import hashlib
import math
import re

TOKEN = re.compile(r"[a-z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+", re.I)


def tokenize(text: str) -> list[str]:
    toks = TOKEN.findall(text.lower())
    grams: list[str] = []
    for tok in toks:
        if len(tok) < 2:
            continue
        grams.append(tok)
        if len(tok) >= 3:
            grams.extend(tok[i : i + 3] for i in range(len(tok) - 2))
    return grams


def embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic hashing embedder. No model download, stable across runs."""
    vec = [0.0] * dim
    for tok in tokenize(text):
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
