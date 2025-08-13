from __future__ import annotations

import argparse
import os
from typing import Dict, Iterable, List, Sequence, Tuple

from .csv_loader import read_policy_csv
from .diff_engine import compare_rules, find_similar_rules, group_by_identity
from .merger import merge_fields, write_merged_csv
from .models import PolicyRule


KEY_FIELDS_TO_SHOW: Sequence[str] = (
    "policyid",
    "name",
    "srcintf",
    "dstintf",
    "srcaddr",
    "dstaddr",
    "service",
    "schedule",
    "action",
    "nat",
)


def _fmt_rule(rule: PolicyRule) -> str:
    parts = [f"[{rule.source_fortigate}] "]
    for k in KEY_FIELDS_TO_SHOW:
        val = rule.raw.get(k, "")
        parts.append(f"{k}='{val}'")
    return ", ".join(parts)


def _print_diff(rule_a: PolicyRule, rule_b: PolicyRule, fields: Sequence[str]) -> None:
    diffs = compare_rules(rule_a, rule_b, fields)
    if not diffs:
        print("No field-level differences in selected fields.")
        return
    print("Differing fields:")
    for field, (a_v, b_v) in diffs.items():
        print(f"  - {field}: A='{a_v}' | B='{b_v}'")


def _gather_active_rules(all_rules: Iterable[PolicyRule], active_ids: Iterable[int]) -> List[PolicyRule]:
    allowed = set(active_ids)
    return [r for r in all_rules if id(r) in allowed]


def interactive_merge(file_paths: List[str], output_path: str, min_similarity: float = 0.2) -> None:
    policy_sets = [read_policy_csv(p) for p in file_paths]
    all_rules: List[PolicyRule] = [r for ps in policy_sets for r in ps.rules]
    active: Dict[int, PolicyRule] = {id(r): r for r in all_rules}

    print(f"Loaded {len(file_paths)} files, total rules: {len(all_rules)}")

    # Prepare identical pairs
    identity_groups = group_by_identity(all_rules)
    identical_pairs: List[Tuple[PolicyRule, PolicyRule]] = []
    for rules in identity_groups.values():
        if len(rules) > 1:
            # Pairwise comparisons
            for i in range(len(rules)):
                for j in range(i + 1, len(rules)):
                    identical_pairs.append((rules[i], rules[j]))

    # Prepare similarity suggestions
    suggestions = find_similar_rules(all_rules, min_similarity=min_similarity)

    queue: List[Tuple[str, Tuple[PolicyRule, PolicyRule]]] = []
    for a, b in identical_pairs:
        queue.append(("identical", (a, b)))
    for s in suggestions:
        queue.append(("similar", (s.rule_a, s.rule_b)))

    print(f"Identical pairs: {len(identical_pairs)} | Similar pairs: {len(suggestions)}")

    idx = 0
    while idx < len(queue):
        kind, (a, b) = queue[idx]
        if id(a) not in active or id(b) not in active:
            idx += 1
            continue

        print("\n---")
        print(f"[{idx+1}/{len(queue)}] {kind.upper()} candidates:")
        print("A:", _fmt_rule(a))
        print("B:", _fmt_rule(b))

        if kind == "similar":
            _print_diff(a, b, fields=("srcaddr", "dstaddr", "service"))

        print("Options:")
        print("  1) Keep A, discard B")
        print("  2) Keep B, discard A")
        print("  3) Keep both (rename B)")
        print("  4) Keep both (rename A)")
        if kind == "similar":
            print("  5) Merge fields into A (srcaddr/dstaddr/service)")
            print("  6) Merge fields into B (srcaddr/dstaddr/service)")
        print("  s) Skip")
        print("  q) Finish and write output")

        choice = input(
            f"Select action for A[{a.source_fortigate}] vs B[{b.source_fortigate}]: "
        ).strip().lower()

        if choice == "1":
            del active[id(b)]
        elif choice == "2":
            del active[id(a)]
        elif choice == "3":
            name_b = b.raw.get("name", "").strip()
            b.raw["name"] = f"{name_b}-from-{b.source_fortigate}" if name_b else f"rule-from-{b.source_fortigate}"
        elif choice == "4":
            name_a = a.raw.get("name", "").strip()
            a.raw["name"] = f"{name_a}-from-{a.source_fortigate}" if name_a else f"rule-from-{a.source_fortigate}"
        elif choice == "5" and kind == "similar":
            merged = merge_fields(a, b, fields=("srcaddr", "dstaddr", "service"))
            a.raw.update(merged)
            del active[id(b)]
        elif choice == "6" and kind == "similar":
            merged = merge_fields(b, a, fields=("srcaddr", "dstaddr", "service"))
            b.raw.update(merged)
            del active[id(a)]
        elif choice == "s":
            idx += 1
            continue
        elif choice == "q":
            break
        else:
            print("Invalid choice; please try again.")
            continue

        idx += 1

    final_rules = _gather_active_rules(all_rules, active.keys())
    print(f"Writing merged CSV with {len(final_rules)} rules → {output_path}")
    write_merged_csv(output_path, final_rules)
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Policy Merger")
    parser.add_argument("files", nargs="+", help="CSV files to load")
    parser.add_argument("--out", required=True, help="Path to write merged CSV")
    parser.add_argument("--min-similarity", type=float, default=0.2)
    args = parser.parse_args()

    csv_files = [f for f in args.files if os.path.exists(f)]
    if not csv_files:
        raise SystemExit("No valid CSV files provided")

    interactive_merge(csv_files, args.out, min_similarity=args.min_similarity)


if __name__ == "__main__":
    main()


