from __future__ import annotations

import argparse
import os
from typing import List

from .csv_loader import read_policy_csv
from .diff_engine import find_similar_rules, group_by_identity


def summarize(file_paths: List[str]) -> None:
    policy_sets = [read_policy_csv(p) for p in file_paths]
    total_rules = sum(len(ps.rules) for ps in policy_sets)
    print(f"Loaded {len(policy_sets)} files, total rules: {total_rules}")
    for ps in policy_sets:
        print(f"- {ps.source_fortigate}: {len(ps.rules)} rules")

    # Combine all rules for initial suggestions
    all_rules = [r for ps in policy_sets for r in ps.rules]
    identical_groups = group_by_identity(all_rules)
    num_identical = sum(1 for rules in identical_groups.values() if len(rules) > 1)
    print(f"Identical rule-groups (by identity signature): {num_identical}")

    suggestions = find_similar_rules(all_rules)
    print(f"Similarity suggestions: {len(suggestions)}")
    for s in suggestions[:10]:
        print(
            f"  ~ {s.rule_a.raw.get('name','')} [{s.rule_a.source_fortigate}] ↔ "
            f"{s.rule_b.raw.get('name','')} [{s.rule_b.source_fortigate}] | score={s.similarity_score:.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Policy Merger CLI")
    parser.add_argument("files", nargs="+", help="CSV files to load")
    args = parser.parse_args()

    csv_files = [f for f in args.files if os.path.exists(f)]
    if not csv_files:
        raise SystemExit("No valid CSV files provided")

    summarize(csv_files)


if __name__ == "__main__":
    main()


