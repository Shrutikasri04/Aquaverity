"""
Optional LLM-polish layer for the Decision Engine's explanation text.

This is OFF by default and never required for the pipeline to work: the
Decision Engine already produces a safe, deterministic summary from
computed values (see decision_engine.py). If ANTHROPIC_API_KEY is set in
the environment, this module asks an LLM to rephrase that same content
more naturally for an end user.

Important: the LLM is only ever given values that have ALREADY been
computed deterministically (label, factors, the template summary). It is
never asked to invent a number, threshold, or fact — only to phrase
existing facts more naturally. If the call fails for any reason (no key,
no network, timeout, bad response), this returns None and the caller
should keep using the deterministic summary. A missing key or a flaky
network must never break the demo.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Optional

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"  # update if your org standardizes on a different model
TIMEOUT_SECONDS = 8


def generate_llm_explanation(
    label: str,
    factors: list[dict[str, Any]],
    deterministic_summary: str,
) -> Optional[str]:
    """
    Ask an LLM to rephrase an already-computed decision more naturally.

    Returns None if ANTHROPIC_API_KEY isn't set or the call fails for any
    reason — callers should fall back to `deterministic_summary` in that case.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    prompt = (
        "Rewrite this marine-safety advisory summary in 2-3 plain, "
        "reassuring-but-honest sentences aimed at a small-scale fisherman. "
        "Do not invent any numbers, thresholds, or facts beyond what's given "
        "below — only rephrase them more naturally.\n\n"
        f"Decision label: {label}\n"
        f"Factors: {json.dumps(factors)}\n"
        f"Deterministic summary to base this on: {deterministic_summary}"
    )

    body = json.dumps(
        {
            "model": MODEL,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        result = " ".join(text_blocks).strip()
        return result or None
    except Exception:
        # Network error, bad key, rate limit, malformed response, etc.
        # Silently degrade to the deterministic summary — never crash the demo.
        return None
