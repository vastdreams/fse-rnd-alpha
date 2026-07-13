"""Deterministic AI-language measurements for transcript backfills."""

from __future__ import annotations

import json
import re
from typing import Any


_AI_PHRASES = [
    "artificial intelligence",
    "generative ai",
    "gen ai",
    "genai",
    "large language model",
    "foundation model",
    "machine learning",
    "deep learning",
    "neural network",
    "ai-powered",
    "ai powered",
    "ai assistant",
    "ai agent",
    "agentic",
    "ai capabilities",
    "ai model",
    "ai feature",
    "ai tool",
    "ai product",
    "copilot",
    "co-pilot",
    "chatgpt",
    "autonomous agent",
]
_AI_TOKENS = [r"\bai\b", r"\bllm\b", r"\bllms\b", r"\bgpt\b", r"\bgpt-\d", r"\bml\b"]
_AI_RE = re.compile("|".join(_AI_PHRASES + _AI_TOKENS), re.IGNORECASE)
_AUG_RE = re.compile(
    "|".join(
        map(
            re.escape,
            [
                "augment",
                "assist",
                "copilot",
                "co-pilot",
                "empower",
                "productivity",
                "enhance",
                "human-in-the-loop",
                "augmentation",
                "complement",
                "amplify",
                "force multiplier",
                "boost",
                "accelerate our customers",
                "help our customers",
            ],
        )
    ),
    re.IGNORECASE,
)
_AUTO_RE = re.compile(
    "|".join(
        map(
            re.escape,
            [
                "automate",
                "automation",
                "replace",
                "autonomous",
                "eliminate",
                "headcount",
                "displace",
                "deflect",
                "without human",
                "fully automated",
                "reduce labor",
                "self-serve",
                "self-service",
                "fewer agents",
                "fewer employees",
            ],
        )
    ),
    re.IGNORECASE,
)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_SEAT_RE = re.compile(
    "|".join(
        map(
            re.escape,
            [
                "per seat",
                "per-seat",
                "per user",
                "per-user",
                "named user",
                "seat-based",
                "per employee",
                "subscription revenue",
                "subscription license",
                "license per",
            ],
        )
    ),
    re.IGNORECASE,
)
_USAGE_RE = re.compile(
    "|".join(
        map(
            re.escape,
            [
                "consumption",
                "usage-based",
                "usage based",
                "consumption-based",
                "per transaction",
                "pay as you go",
                "pay-as-you-go",
                "metered",
                "credits",
                "compute usage",
                "per gigabyte",
                "per query",
                "per api call",
            ],
        )
    ),
    re.IGNORECASE,
)
_ANALYST_HINT = re.compile(r"analyst", re.IGNORECASE)


def _as_segments(payload: Any) -> list[dict]:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return []
    if isinstance(payload, dict):
        segments = payload.get("transcript")
        return segments if isinstance(segments, list) else []
    return []


def _score_text(text: str) -> tuple[int, int, int, int]:
    if not text:
        return 0, 0, 0, 0
    sentences = _SENT_SPLIT.split(text)
    n_sentences = n_ai = n_augment = n_automate = 0
    for sentence in sentences:
        if not sentence.strip():
            continue
        n_sentences += 1
        if _AI_RE.search(sentence):
            n_ai += 1
            n_augment += len(_AUG_RE.findall(sentence))
            n_automate += len(_AUTO_RE.findall(sentence))
    return n_sentences, n_ai, n_augment, n_automate


def _measure_one(segments: list[dict]) -> dict[str, float | int]:
    total_sentences = total_ai = total_augment = total_automate = 0
    qa_sentences = qa_ai = n_seat = n_usage = 0
    for segment in segments:
        content = segment.get("content") if isinstance(segment, dict) else None
        title = segment.get("title") or "" if isinstance(segment, dict) else ""
        n_sentences, n_ai, n_augment, n_automate = _score_text(content or "")
        total_sentences += n_sentences
        total_ai += n_ai
        total_augment += n_augment
        total_automate += n_automate
        if content:
            n_seat += len(_SEAT_RE.findall(content))
            n_usage += len(_USAGE_RE.findall(content))
        if _ANALYST_HINT.search(title):
            qa_sentences += n_sentences
            qa_ai += n_ai
    aiexp = total_ai / total_sentences if total_sentences else 0.0
    denominator = total_augment + total_automate
    stance = (total_augment - total_automate) / denominator if denominator else 0.0
    return {
        "n_sentences": total_sentences,
        "n_ai_sentences": total_ai,
        "aiexp": aiexp,
        "stance": stance,
        "vuln_raw": aiexp * (1.0 - stance) / 2.0,
        "aiexp_qa": qa_ai / qa_sentences if qa_sentences else 0.0,
        "n_aug": total_augment,
        "n_auto": total_automate,
        "n_seat": n_seat,
        "n_usage": n_usage,
    }
