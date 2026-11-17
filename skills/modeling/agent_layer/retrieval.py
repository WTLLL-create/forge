"""Lightweight BM25 retrieval over the modeling knowledge base.

No embedding service, no network: the index is built from Markdown files under
``skills/modeling``. That keeps retrieval deterministic and testable offline,
while the same interface can later be swapped for a vector store.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CJK = r"\u4e00-\u9fff"
TOKEN_RE = re.compile(f"[a-z0-9_]+|[{CJK}]")

KNOWLEDGE_DIRS = (
    "paper_pattern_library",
    "reviewer_agent",
    "paper_reasoning",
    "visual_engineering",
    "evidence_layer",
    "problem_intelligence",
)

MAX_CHARS_PER_DOC = 6000


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    units = TOKEN_RE.findall(lowered)
    bigrams = [
        "".join(pair)
        for pair in zip(units, units[1:])
        if all(re.fullmatch(f"[{CJK}]", unit) for unit in pair)
    ]
    return units + bigrams


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    path: str
    text: str


@dataclass(frozen=True)
class Hit:
    doc_id: str
    title: str
    path: str
    score: float
    snippet: str


def _snippet(text: str, query: str, width: int = 90) -> str:
    needle = query.strip()
    if needle and needle in text:
        index = text.find(needle)
    else:
        tokens = [t for t in tokenize(query) if len(t) > 1]
        index = min((text.find(t) for t in tokens if t in text), default=-1)
    if index < 0:
        return text[: width * 2].replace("\n", " ").strip()
    start = max(0, index - width)
    end = min(len(text), index + len(needle or query) + width)
    return text[start:end].replace("\n", " ").strip()


class BM25Index:
    def __init__(self, documents: Iterable[Document], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self._tokens = [tokenize(f"{doc.title} {doc.text}") for doc in self.documents]
        self._doc_len = [len(tokens) for tokens in self._tokens]
        self._avg_len = sum(self._doc_len) / max(len(self._doc_len), 1)
        self._postings: dict[str, dict[int, int]] = {}
        for index, tokens in enumerate(self._tokens):
            counts: dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            for token, tf in counts.items():
                self._postings.setdefault(token, {})[index] = tf
        self.n_docs = len(self.documents)

    def _idf(self, term: str) -> float:
        df = len(self._postings.get(term, {}))
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 5) -> list[Hit]:
        if not self.documents or not query.strip():
            return []
        scores = [0.0] * self.n_docs
        for term in tokenize(query):
            postings = self._postings.get(term)
            if not postings:
                continue
            idf = self._idf(term)
            for index, tf in postings.items():
                length = self._doc_len[index] or 1
                denominator = tf + self.k1 * (1 - self.b + self.b * length / self._avg_len)
                scores[index] += idf * tf * (self.k1 + 1) / denominator
        ranked = sorted(range(self.n_docs), key=lambda i: scores[i], reverse=True)[:top_k]
        hits: list[Hit] = []
        for index in ranked:
            if scores[index] <= 0:
                continue
            doc = self.documents[index]
            hits.append(
                Hit(
                    doc.doc_id,
                    doc.title,
                    doc.path,
                    round(scores[index], 4),
                    _snippet(doc.text, query),
                )
            )
        return hits


def build_index(root: Path, extra_dirs: Iterable[Path] = ()) -> BM25Index:
    """Index every Markdown rule under the given knowledge directories."""
    documents: list[Document] = []
    for name in KNOWLEDGE_DIRS:
        base = root / name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")[:MAX_CHARS_PER_DOC]
            documents.append(
                Document(
                    doc_id=f"{name}/{path.relative_to(base).as_posix()}",
                    title=path.stem,
                    path=str(path),
                    text=text,
                )
            )
    for extra in extra_dirs:
        if not extra.is_dir():
            continue
        for path in sorted(extra.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")[:MAX_CHARS_PER_DOC]
            documents.append(
                Document(
                    doc_id=f"extra/{path.relative_to(extra).as_posix()}",
                    title=path.stem,
                    path=str(path),
                    text=text,
                )
            )
    if not documents:
        raise RuntimeError(f"no knowledge documents found under {root}")
    return BM25Index(documents)
