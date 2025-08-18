from __future__ import annotations

from policy_merger.models import PolicyRule
from policy_merger.diff_engine import deduplicate_identical_rules, group_similarity_suggestions


def make_rule(name: str, src: str, dst: str, svc: str, device: str = "FG1") -> PolicyRule:
    raw = {
        "name": name,
        "srcintf": "port1",
        "dstintf": "port2",
        "srcaddr": src,
        "dstaddr": dst,
        "service": svc,
        "schedule": "always",
        "action": "accept",
        "nat": "disable",
    }
    return PolicyRule(raw=raw, source_fortigate=device)


def test_deduplicate_identical_rules():
    a = make_rule("A", "SRC1", "DST1", "ALL")
    b = make_rule("B", "SRC1", "DST1", "ALL")  # identical by identity signature
    c = make_rule("C", "SRC2", "DST2", "ALL")

    unique, removed = deduplicate_identical_rules([a, b, c])
    assert len(unique) == 2
    assert removed == 1


def test_group_similarity_suggestions_merges_pairs():
    # Same non-candidate fields; candidate fields differ slightly to trigger suggestions
    a = make_rule("A", "SRC1 SRC2", "DST1", "HTTP")
    b = make_rule("B", "SRC1", "DST1", "HTTP HTTPS")
    c = make_rule("C", "SRC1 SRC2", "DST1", "HTTP")  # identical to A in candidate fields

    grouped = group_similarity_suggestions([a, b, c])
    # There should be at least one group
    assert len(grouped) >= 1
    # Each group is a list of suggestions
    for suggestions in grouped.values():
        assert isinstance(suggestions, list)
        # Each suggestion has rule_a and rule_b
        if suggestions:
            s = suggestions[0]
            assert hasattr(s, "rule_a") and hasattr(s, "rule_b")
