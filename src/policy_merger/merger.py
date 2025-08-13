from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from .models import PolicyRule, PolicySet
from .csv_loader import write_policy_csv


def _normalize_space(value: str) -> str:
    return " ".join((value or "").strip().split())


def _tokenize(value: str) -> List[str]:
    norm = _normalize_space(value)
    if not norm:
        return []
    return norm.split(" ")


def _join_tokens(a_tokens: Sequence[str], b_tokens: Sequence[str]) -> str:
    seen = set()
    ordered: List[str] = []
    for token in list(a_tokens) + list(b_tokens):
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return " ".join(ordered)


def merge_fields(rule_a: PolicyRule, rule_b: PolicyRule, fields: Sequence[str]) -> Dict[str, str]:
    merged = dict(rule_a.raw)
    for field in fields:
        tokens_a = _tokenize(rule_a.raw.get(field, ""))
        tokens_b = _tokenize(rule_b.raw.get(field, ""))
        merged[field] = _join_tokens(tokens_a, tokens_b)
    return merged


def keep_both_rename(rule_a: PolicyRule, rule_b: PolicyRule) -> Tuple[Dict[str, str], Dict[str, str]]:
    a = dict(rule_a.raw)
    b = dict(rule_b.raw)
    name_field = "name"
    if name_field in a:
        a[name_field] = f"{a.get(name_field, '').strip()}-from-{rule_a.source_fortigate}"
    if name_field in b:
        b[name_field] = f"{b.get(name_field, '').strip()}-from-{rule_b.source_fortigate}"
    return a, b


def union_columns(policy_sets: Iterable[PolicySet]) -> List[str]:
    cols: List[str] = []
    seen = set()
    for ps in policy_sets:
        for c in ps.columns:
            if c not in seen:
                seen.add(c)
                cols.append(c)
    return cols


def write_merged_csv(path: str, rules: List[PolicyRule], preferred_columns: Sequence[str] | None = None) -> None:
    # Build a synthetic PolicySet to leverage existing writer
    # Determine columns by union across rules or use preferred
    if preferred_columns is None:
        seen = set()
        cols: List[str] = []
        for rule in rules:
            for c in rule.raw.keys():
                if c not in seen:
                    seen.add(c)
                    cols.append(c)
    else:
        cols = list(preferred_columns)
    synthetic = PolicySet(source_fortigate="MERGED", columns=cols)
    for r in rules:
        # Ensure all columns present
        row = {c: r.raw.get(c, "") for c in cols}
        synthetic.add_rule(row)
    write_policy_csv(path, synthetic)


