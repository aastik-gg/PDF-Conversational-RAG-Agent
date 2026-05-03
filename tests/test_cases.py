"""
Predefined queries for manual QA and optional live API tests.

Grounded in: **PM_OneNight_MasterGuide.pdf** (Product Management — Learn It Tonight,
Ace It Tomorrow). Place a copy at ``tests/fixtures/PM_OneNight_MasterGuide.pdf`` (included
in this repo) or upload the same file via ``POST /upload`` before running chat tests.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# --- Reference document (44-page consolidated PM guide, Indian app examples) ---

REFERENCE_PDF_FILENAME = "PM_OneNight_MasterGuide.pdf"
REFERENCE_PDF_FIXTURE = Path(__file__).resolve().parent / "fixtures" / REFERENCE_PDF_FILENAME

# --- 5 valid queries: answerable from the guide (expected pages are indicative) ---

VALID_QUERIES: list[dict[str, str]] = [
    {
        "query": (
            "According to this guide, what is the North Star Metric (NSM) "
            "and how is it defined?"
        ),
        "expected_behavior": (
            "Should state it is the single number that captures core customer value / "
            "the one metric that best captures the value customers get; cite Topic 7 area "
            "(e.g. around page 11). Refusal would be wrong if NSM is defined in retrieved chunks."
        ),
    },
    {
        "query": (
            "In the Jobs-To-Be-Done section, what example is used with Ola and what "
            "point does it illustrate?"
        ),
        "expected_behavior": (
            "Should describe hiring Ola late at night for getting home safely vs "
            "metro for office — product as means, job as reason; cite pages where JTBD "
            "topic appears (e.g. ~page 4–5)."
        ),
    },
    {
        "query": (
            "What contrast does the guide draw between an output and an outcome, "
            "including one example from its table?"
        ),
        "expected_behavior": (
            "Output vs outcome (e.g. shipped feature vs behavior/revenue change); "
            "example like UPI button vs more payments completed; cite ~page 3."
        ),
    },
    {
        "query": (
            "नॉर्थ स्टार मीट्रिक की परिभाषा इस गाइड के अनुसार क्या है? "
            "संक्षेप में हिंदी में बताएं।"
        ),
        "expected_behavior": (
            "Answer in Hindi, grounded in the same NSM definition as English; "
            "include (Page …) style citations. Must not refuse as out-of-document "
            "if retrieval + translation pipeline is working."
        ),
    },
    {
        "query": (
            "What OKR format does the document show (Objective vs KRs) and what "
            "Swiggy PM example objective is given for Q2?"
        ),
        "expected_behavior": (
            "Mentions objective with measurable KRs / tree structure; Swiggy example "
            "about fastest food delivery in metro India with sample KRs; cite ~page 22."
        ),
    },
]

# --- 3 invalid queries: not answered by this PM guide ---

INVALID_QUERIES: list[dict[str, str]] = [
    {
        "query": (
            "Write a production-ready React component with hooks that implements "
            "infinite scroll with virtualization."
        ),
        "expected_behavior": (
            'Refusal: "This question is outside the provided document." '
            "(Guide is PM concepts, not React/JavaScript tutorials.)"
        ),
    },
    {
        "query": "What was the exact closing price of Tesla stock on March 3, 2020?",
        "expected_behavior": (
            'Refusal or "This information is not available in the document." '
            "(No live stock data in a static PM PDF.)"
        ),
    },
    {
        "query": (
            "Derive the time complexity of the Cooley–Tukey FFT algorithm "
            "and prove the master theorem."
        ),
        "expected_behavior": (
            'Refusal: "This question is outside the provided document." '
            "(Algorithms / proofs not in scope.)"
        ),
    },
]


def describe_test_matrix() -> str:
    """Human-readable summary for README or manual QA."""
    lines = [
        f"Reference PDF: {REFERENCE_PDF_FILENAME} (fixture: {REFERENCE_PDF_FIXTURE})",
        "",
        "=== Valid queries (expect grounded answer + citations) ===",
    ]
    for i, item in enumerate(VALID_QUERIES, 1):
        lines.append(f"{i}. Q: {item['query']}\n   Expected: {item['expected_behavior']}")
    lines.append("\n=== Invalid queries (expect refusal) ===")
    for i, item in enumerate(INVALID_QUERIES, 1):
        lines.append(f"{i}. Q: {item['query']}\n   Expected: {item['expected_behavior']}")
    return "\n".join(lines)


def _live_enabled() -> bool:
    return os.getenv("RUN_LIVE_API_TESTS", "").lower() in ("1", "true", "yes")


def test_reference_fixture_exists() -> None:
    """The bundled PDF fixture is present for local upload / demos."""
    assert REFERENCE_PDF_FIXTURE.is_file(), (
        f"Missing {REFERENCE_PDF_FIXTURE}. Restore from repo or copy "
        f"{REFERENCE_PDF_FILENAME} into tests/fixtures/."
    )


def test_live_chat_pipeline() -> None:
    """Requires server on TEST_BASE_URL and the PM guide already uploaded as active PDF."""
    import pytest

    if not _live_enabled():
        pytest.skip("Set RUN_LIVE_API_TESTS=1 to hit the real API.")

    import httpx

    base = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    with httpx.Client(base_url=base, timeout=120.0) as client:
        h = client.get("/health")
        assert h.status_code == 200
        q = VALID_QUERIES[0]["query"]
        r = client.post("/chat", json={"question": q})
        assert r.status_code == 200, r.text
        data: dict[str, Any] = r.json()
        assert "answer" in data
        assert len(data["answer"]) > 0


def test_case_catalog_non_empty() -> None:
    assert len(VALID_QUERIES) == 5
    assert len(INVALID_QUERIES) == 3
    for row in VALID_QUERIES + INVALID_QUERIES:
        assert "query" in row and "expected_behavior" in row


def _run_all_questions_against_api() -> None:
    """
    Print real /chat answers for every catalog row (needs running server + active PDF).

    Usage (from project root, venv on):
        uvicorn app.main:app --port 8000   # other terminal
        # upload tests/fixtures/PM_OneNight_MasterGuide.pdf via UI or curl
        python tests/test_cases.py --api
    """
    import httpx

    base = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    with httpx.Client(base_url=base, timeout=180.0) as client:
        h = client.get("/health")
        if h.status_code != 200:
            raise SystemExit(f"Server not healthy at {base} (GET /health -> {h.status_code})")

        def ask(label: str, row: dict[str, str], n: int) -> None:
            q = row["query"]
            print(f"\n{'=' * 72}\n{label} #{n}\nQ: {q}\nExpected: {row['expected_behavior']}\n{'-' * 72}")
            try:
                r = client.post("/chat", json={"question": q})
                body = r.json() if r.content else {}
                if r.status_code != 200:
                    detail = body.get("detail", r.text)
                    print(f"HTTP {r.status_code}: {detail}")
                    return
                ans = body.get("answer", "")
                cites = body.get("citations", [])
                print(f"A: {ans}")
                if cites:
                    pages = ", ".join(f"p{c.get('page', '?')}" for c in cites)
                    print(f"Citations (retrieval): {pages}")
            except Exception as exc:
                print(f"Error: {exc}")

        print(f"Server: {base}\nDocument: {REFERENCE_PDF_FILENAME} (must be active via prior upload)")
        for i, row in enumerate(VALID_QUERIES, 1):
            ask("VALID", row, i)
        for i, row in enumerate(INVALID_QUERIES, 1):
            ask("INVALID", row, i)
        print(f"\n{'=' * 72}\nDone.")


if __name__ == "__main__":
    import sys

    if "--api" in sys.argv:
        _run_all_questions_against_api()
    else:
        print(describe_test_matrix())
        print(
            "\n---\n"
            "This printout is only the **question rubric**, not live answers.\n"
            "To hit your running server for **every** question above:\n"
            "  1) Start: uvicorn app.main:app --reload\n"
            "  2) Upload: tests/fixtures/PM_OneNight_MasterGuide.pdf\n"
            "  3) Run:   python tests/test_cases.py --api\n"
            "(Optional: TEST_BASE_URL=http://127.0.0.1:8000)\n"
            "For a single automated smoke test, use: pytest + RUN_LIVE_API_TESTS=1\n"
        )
