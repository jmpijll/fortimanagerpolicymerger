from __future__ import annotations

import argparse
import os
from typing import Dict, List, Tuple

from .csv_loader import read_policy_csv
from .models import PolicyRule
from .merger import write_merged_csv


def batch_merge(file_paths: List[str], output_path: str) -> Tuple[int, int]:
    policy_sets = [read_policy_csv(p) for p in file_paths]
    all_rules: List[PolicyRule] = [r for ps in policy_sets for r in ps.rules]

    kept_by_signature: Dict[Tuple[str, ...], PolicyRule] = {}
    for rule in all_rules:
        sig = rule.identity_signature()
        if sig not in kept_by_signature:
            kept_by_signature[sig] = rule
        # else: drop duplicates by identity signature

    kept_rules = list(kept_by_signature.values())
    write_merged_csv(output_path, kept_rules)
    return len(all_rules), len(kept_rules)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch merge (deduplicate identical rules)")
    parser.add_argument("files", nargs="+", help="CSV files to load")
    parser.add_argument("--out", required=True, help="Path to write merged CSV")
    args = parser.parse_args()

    csv_files = [f for f in args.files if os.path.exists(f)]
    if not csv_files:
        raise SystemExit("No valid CSV files provided")

    total, kept = batch_merge(csv_files, args.out)
    print(f"Merged {len(csv_files)} files: kept {kept}/{total} rules (removed {total - kept} duplicates)")


if __name__ == "__main__":
    main()


