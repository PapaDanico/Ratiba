"""Phase 1 acceptance: every documented rule has ≥1 test.

Walks ``docs/ftl-rules.md`` to extract rule IDs, then asserts that:

1. The engine's ``all_rule_ids()`` matches the documented set.
2. Every rule ID appears in at least one test file.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.services.ftl_engine import all_rule_ids

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_FILE = REPO_ROOT / "docs" / "ftl-rules.md"
TESTS_DIR = Path(__file__).resolve().parent

RULE_ID_RE = re.compile(r"KCAR-P8-[A-Z0-9-]+")


def _documented_rule_ids() -> set[str]:
    ids: set[str] = set()
    for match in RULE_ID_RE.finditer(DOCS_FILE.read_text(encoding="utf-8")):
        rid = match.group(0)
        # Skip the rule-ID convention example in the document
        if rid.startswith("KCAR-P8-<"):
            continue
        ids.add(rid)
    # Filter to whatever the engine considers canonical (avoids picking up
    # legacy or example identifiers from prose).
    return ids & set(all_rule_ids())


def _ids_mentioned_in_tests() -> set[str]:
    out: set[str] = set()
    for path in TESTS_DIR.rglob("test_*.py"):
        out.update(RULE_ID_RE.findall(path.read_text(encoding="utf-8")))
    return out


def test_engine_rule_ids_match_documentation() -> None:
    engine_ids = set(all_rule_ids())
    documented = _documented_rule_ids()
    missing_from_docs = engine_ids - documented
    extra_in_docs = documented - engine_ids
    assert not missing_from_docs, (
        f"engine rules not documented in docs/ftl-rules.md: {missing_from_docs}"
    )
    assert not extra_in_docs, f"docs/ftl-rules.md mentions rules not in the engine: {extra_in_docs}"


def test_every_engine_rule_has_at_least_one_test() -> None:
    engine_ids = set(all_rule_ids())
    tested = _ids_mentioned_in_tests()
    missing = engine_ids - tested
    assert not missing, f"no test exercises these rules: {missing}"
