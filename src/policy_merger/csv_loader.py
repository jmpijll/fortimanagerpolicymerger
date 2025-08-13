from __future__ import annotations

import os
import re
from typing import List, Tuple

import pandas as pd

from .models import PolicySet


HEADER_KEY = "policyid"
SOURCE_TAG_REGEX = re.compile(r"^(?P<device>.+?)-\d{8}-\d{6}$")


def derive_source_fortigate_tag(path: str) -> str:
    base = os.path.basename(path)
    name, _ext = os.path.splitext(base)
    m = SOURCE_TAG_REGEX.match(name)
    return m.group("device") if m else name


def find_header_row(path: str, encoding: str = "utf-8") -> int:
    with open(path, "r", encoding=encoding, errors="replace") as fh:
        for idx, line in enumerate(fh):
            if HEADER_KEY in line:
                return idx
    raise ValueError(f"Could not locate header containing '{HEADER_KEY}' in: {path}")


def read_policy_csv(path: str, encoding: str = "utf-8") -> PolicySet:
    header_row = find_header_row(path, encoding=encoding)
    df = pd.read_csv(
        path,
        header=header_row,
        dtype=str,
        keep_default_na=False,
        na_values=[],
        encoding=encoding,
        engine="python",
    )
    df.columns = [c.strip() for c in df.columns]

    source_tag = derive_source_fortigate_tag(path)
    policy_set = PolicySet(source_fortigate=source_tag, columns=list(df.columns))

    for _, row in df.iterrows():
        raw = {col: (str(row[col]) if row[col] is not None else "") for col in df.columns}
        policy_set.add_rule(raw)

    return policy_set


def write_policy_csv(path: str, policy_set: PolicySet, encoding: str = "utf-8") -> None:
    # Preserve column order if available; otherwise infer from first row
    columns: List[str] = policy_set.columns
    if not columns and policy_set.rules:
        columns = list(policy_set.rules[0].raw.keys())
    df = pd.DataFrame(policy_set.to_rows(), columns=columns)
    df.to_csv(path, index=False, encoding=encoding)


