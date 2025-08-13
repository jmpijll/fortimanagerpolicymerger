from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PolicyRule:
    raw: Dict[str, str]
    source_fortigate: str

    def identity_signature(self) -> tuple:
        def norm(value: Optional[str]) -> str:
            if value is None:
                return ""
            return " ".join(value.strip().split()).lower()

        key_fields = [
            "srcintf",
            "dstintf",
            "srcaddr",
            "dstaddr",
            "service",
            "schedule",
            "action",
            "nat",
        ]
        return tuple(norm(self.raw.get(k)) for k in key_fields)


@dataclass
class PolicySet:
    source_fortigate: str
    rules: List[PolicyRule] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)

    def add_rule(self, raw_row: Dict[str, str]) -> None:
        self.rules.append(PolicyRule(raw=raw_row, source_fortigate=self.source_fortigate))

    def to_rows(self) -> List[Dict[str, str]]:
        return [r.raw for r in self.rules]

