from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .models import PolicyRule
FIVE_FIELDS: Tuple[str, str, str, str, str] = (
    "srcaddr",
    "dstaddr",
    "srcintf",
    "dstintf",
    "service",
)

# Minimal context fields to anchor suggestions. These are typically stable across near-duplicates.
STABLE_CONTEXT_FIELDS: Tuple[str, ...] = (
    "schedule",
    "action",
    "nat",
    "status",
)



def _normalize_space(value: str) -> str:
    return " ".join((value or "").strip().split())


def _tokenize_multi_value(value: str) -> List[str]:
    # Phase 1: naive space-splitting; later phases will replace with dictionary-aware parsing
    normalized = _normalize_space(value)
    if not normalized:
        return []
    return normalized.split(" ")


def jaccard_similarity(a_tokens: Sequence[str], b_tokens: Sequence[str]) -> float:
    a_set, b_set = set(a_tokens), set(b_tokens)
    if not a_set and not b_set:
        return 1.0
    intersection = len(a_set & b_set)
    union = len(a_set | b_set)
    return intersection / union if union else 0.0


def compare_rules(rule_a: PolicyRule, rule_b: PolicyRule, fields: Sequence[str]) -> Dict[str, Tuple[str, str]]:
    diffs: Dict[str, Tuple[str, str]] = {}
    for field in fields:
        a_val = rule_a.raw.get(field, "")
        b_val = rule_b.raw.get(field, "")
        if _normalize_space(a_val) != _normalize_space(b_val):
            diffs[field] = (a_val, b_val)
    return diffs


def group_by_identity(rules: Iterable[PolicyRule]) -> Dict[Tuple[str, ...], List[PolicyRule]]:
    groups: Dict[Tuple[str, ...], List[PolicyRule]] = defaultdict(list)
    for rule in rules:
        groups[rule.identity_signature()].append(rule)
    return groups


def group_by_stable_key(
    rules: Iterable[PolicyRule], excluded_fields: Sequence[str]
) -> Dict[Tuple[Tuple[str, str], ...], List[PolicyRule]]:
    groups: Dict[Tuple[Tuple[str, str], ...], List[PolicyRule]] = defaultdict(list)
    excluded = set(excluded_fields)
    for rule in rules:
        # Stable key uses all fields except those in excluded_fields
        items = tuple(sorted((k, _normalize_space(v)) for k, v in rule.raw.items() if k not in excluded))
        groups[items].append(rule)
    return groups


def group_by_minimal_context(rules: Iterable[PolicyRule]) -> Dict[Tuple[Tuple[str, str], ...], List[PolicyRule]]:
    """Group rules by a minimal stable context ignoring names/ids and the five key fields.

    This greatly increases the likelihood that near-duplicates differing only in the five
    fields (and names/ids) are grouped together for merge suggestions.
    """
    groups: Dict[Tuple[Tuple[str, str], ...], List[PolicyRule]] = defaultdict(list)
    for rule in rules:
        items = []
        for field in STABLE_CONTEXT_FIELDS:
            items.append((field, _normalize_space(rule.raw.get(field, ""))))
        groups[tuple(items)].append(rule)
    return groups


@dataclass
class SimilaritySuggestion:
    stable_key: Tuple[Tuple[str, str], ...]
    field_diffs: Dict[str, Tuple[str, str]]
    similarity_score: float
    rule_a: PolicyRule
    rule_b: PolicyRule


def find_similar_rules(
    rules: Iterable[PolicyRule],
    candidate_fields: Sequence[str] = ("srcaddr", "dstaddr", "service"),
    min_similarity: float = 0.2,
) -> List[SimilaritySuggestion]:
    suggestions: List[SimilaritySuggestion] = []
    # Exclude variable/non-stable fields from grouping such as name/policyid in addition to candidate fields
    excluded_fields: Tuple[str, ...] = tuple(candidate_fields) + ("name", "policyid")
    groups = group_by_stable_key(rules, excluded_fields=excluded_fields)
    for stable_key, group_rules in groups.items():
        n = len(group_rules)
        if n < 2:
            continue
        for i in range(n):
            for j in range(i + 1, n):
                a, b = group_rules[i], group_rules[j]
                diffs = compare_rules(a, b, candidate_fields)
                if not diffs:
                    # identical within candidate fields; treat as identical overall
                    suggestions.append(
                        SimilaritySuggestion(
                            stable_key=stable_key,
                            field_diffs={},
                            similarity_score=1.0,
                            rule_a=a,
                            rule_b=b,
                        )
                    )
                    continue
                # Compute average Jaccard across multi-value fields that differ
                scores: List[float] = []
                for field, (a_val, b_val) in diffs.items():
                    scores.append(jaccard_similarity(_tokenize_multi_value(a_val), _tokenize_multi_value(b_val)))
                avg_score = sum(scores) / len(scores) if scores else 0.0
                if avg_score >= min_similarity:
                    suggestions.append(
                        SimilaritySuggestion(
                            stable_key=stable_key,
                            field_diffs=diffs,
                            similarity_score=avg_score,
                            rule_a=a,
                            rule_b=b,
                        )
                    )
    return suggestions


def deduplicate_identical_rules(rules: Iterable[PolicyRule]) -> Tuple[List[PolicyRule], int]:
    """Remove exact duplicates based on identity signature, preserving first occurrence.

    Returns a tuple of (unique_rules, num_removed).
    """
    seen: Dict[Tuple[str, ...], PolicyRule] = {}
    unique: List[PolicyRule] = []
    removed = 0
    for r in rules:
        sig = r.identity_signature()
        if sig in seen:
            removed += 1
            continue
        seen[sig] = r
        unique.append(r)
    return unique, removed


def group_similarity_suggestions(
    rules: Iterable[PolicyRule],
    candidate_fields: Sequence[str] = ("srcaddr", "dstaddr", "service"),
    min_similarity: float = 0.2,
) -> Dict[Tuple[Tuple[str, str], ...], List[SimilaritySuggestion]]:
    """Find and group similarity suggestions by stable key (all non-candidate fields).

    This is useful for presenting batch actions per group in the UI.
    """
    grouped: Dict[Tuple[Tuple[str, str], ...], List[SimilaritySuggestion]] = defaultdict(list)
    for s in find_similar_rules(rules, candidate_fields=candidate_fields, min_similarity=min_similarity):
        grouped[s.stable_key].append(s)
    return grouped


def five_field_key(rule: PolicyRule) -> Tuple[str, str, str, str, str]:
    return tuple(_normalize_space(rule.raw.get(field, "")) for field in FIVE_FIELDS)  # type: ignore[return-value]


def group_duplicates_by_five_fields(rules: Iterable[PolicyRule]) -> Dict[Tuple[str, str, str, str, str], List[PolicyRule]]:
    groups: Dict[Tuple[str, str, str, str, str], List[PolicyRule]] = defaultdict(list)
    for r in rules:
        groups[five_field_key(r)].append(r)
    return groups


def deduplicate_by_five_fields(rules: Iterable[PolicyRule]) -> Tuple[List[PolicyRule], Dict[Tuple[str, str, str, str, str], List[PolicyRule]]]:
    groups = group_duplicates_by_five_fields(rules)
    unique: List[PolicyRule] = []
    for key, group in groups.items():
        # keep first, others considered duplicates for review
        unique.append(group[0])
    return unique, groups


def find_merge_suggestions_five_fields(
    rules: Iterable[PolicyRule],
    min_similarity: float = 0.2,
) -> List[SimilaritySuggestion]:
    # Use only five fields for comparisons, other fields ignored
    suggestions: List[SimilaritySuggestion] = []
    # Group by a minimal stable context to catch cases differing only in name/service
    groups = group_by_minimal_context(rules)
    for stable_key, group_rules in groups.items():
        n = len(group_rules)
        if n < 2:
            continue
        for i in range(n):
            for j in range(i + 1, n):
                a, b = group_rules[i], group_rules[j]
                diffs = compare_rules(a, b, FIVE_FIELDS)
                if not diffs:
                    suggestions.append(
                        SimilaritySuggestion(
                            stable_key=stable_key,
                            field_diffs={},
                            similarity_score=1.0,
                            rule_a=a,
                            rule_b=b,
                        )
                    )
                    continue
                scores: List[float] = []
                for field, (a_val, b_val) in diffs.items():
                    scores.append(jaccard_similarity(_tokenize_multi_value(a_val), _tokenize_multi_value(b_val)))
                avg_score = sum(scores) / len(scores) if scores else 0.0
                if avg_score >= min_similarity:
                    suggestions.append(
                        SimilaritySuggestion(
                            stable_key=stable_key,
                            field_diffs=diffs,
                            similarity_score=avg_score,
                            rule_a=a,
                            rule_b=b,
                        )
                    )
    return suggestions


def _extra_tokens(base: str, other: str) -> List[str]:
    base_set = set(_tokenize_multi_value(base))
    other_set = set(_tokenize_multi_value(other))
    return sorted(other_set - base_set)


def build_suggestion_reason(s: SimilaritySuggestion) -> str:
    if not s.field_diffs:
        return "Identical on the five key fields."
    parts: List[str] = []
    for field, (a_val, b_val) in s.field_diffs.items():
        added_to_a = _extra_tokens(a_val, b_val)
        added_to_b = _extra_tokens(b_val, a_val)
        subparts: List[str] = []
        if added_to_a:
            subparts.append(f"add to A: {', '.join(added_to_a)}")
        if added_to_b:
            subparts.append(f"add to B: {', '.join(added_to_b)}")
        if subparts:
            parts.append(f"{field} (" + "; ".join(subparts) + ")")
        else:
            parts.append(f"{field} differs")
    return "; ".join(parts)


