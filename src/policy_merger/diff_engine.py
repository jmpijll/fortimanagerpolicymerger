from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .models import PolicyRule


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
    groups = group_by_stable_key(rules, excluded_fields=candidate_fields)
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


