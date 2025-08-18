from __future__ import annotations

from typing import Dict, Tuple, List

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QPushButton, QGroupBox, QHBoxLayout, QCheckBox

from policy_merger.diff_engine import compare_rules
from policy_merger.models import PolicyRule
from policy_merger.merger import merge_fields


class MergeDialog(QDialog):
    def __init__(self, rule_a: PolicyRule, rule_b: PolicyRule, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resolve Similar Rules")
        self.rule_a = rule_a
        self.rule_b = rule_b
        self.result_choice: str | None = None
        self.selected_fields: List[str] = ["srcaddr", "dstaddr", "service"]

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"A from {rule_a.source_fortigate}: {rule_a.raw.get('name','')}", self))
        layout.addWidget(QLabel(f"B from {rule_b.source_fortigate}: {rule_b.raw.get('name','')}", self))

        diffs = compare_rules(rule_a, rule_b, fields=("srcaddr", "dstaddr", "service"))
        if diffs:
            layout.addWidget(QLabel("Differing fields:", self))
            for field, (a_v, b_v) in diffs.items():
                layout.addWidget(QLabel(f"- {field}: A='{a_v}' | B='{b_v}'", self))

        # Field selection for merge actions
        fields_box = QGroupBox("Fields to merge", self)
        fields_layout = QHBoxLayout(fields_box)
        self._cb_src = QCheckBox("srcaddr", fields_box)
        self._cb_dst = QCheckBox("dstaddr", fields_box)
        self._cb_svc = QCheckBox("service", fields_box)
        for cb in (self._cb_src, self._cb_dst, self._cb_svc):
            cb.setChecked(True)
            fields_layout.addWidget(cb)
        layout.addWidget(fields_box)

        btn_keep_a = QPushButton("Keep A / discard B", self)
        btn_keep_b = QPushButton("Keep B / discard A", self)
        btn_keep_both = QPushButton("Keep both (rename)", self)
        btn_merge_into_a = QPushButton("Merge selected into A", self)
        btn_merge_into_b = QPushButton("Merge selected into B", self)

        layout.addWidget(btn_keep_a)
        layout.addWidget(btn_keep_b)
        layout.addWidget(btn_keep_both)
        layout.addWidget(btn_merge_into_a)
        layout.addWidget(btn_merge_into_b)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        layout.addWidget(buttons)

        btn_keep_a.clicked.connect(self._choose_keep_a)
        btn_keep_b.clicked.connect(self._choose_keep_b)
        btn_keep_both.clicked.connect(self._choose_keep_both)
        btn_merge_into_a.clicked.connect(self._choose_merge_into_a)
        btn_merge_into_b.clicked.connect(self._choose_merge_into_b)
        buttons.rejected.connect(self.reject)

    def _choose_keep_a(self) -> None:
        self.result_choice = "keep_a"
        self.accept()

    def _choose_keep_b(self) -> None:
        self.result_choice = "keep_b"
        self.accept()

    def _choose_keep_both(self) -> None:
        self.result_choice = "keep_both"
        self.accept()

    def _choose_merge_into_a(self) -> None:
        self.result_choice = "merge_into_a"
        self.selected_fields = self._get_selected_fields()
        self.accept()

    def _choose_merge_into_b(self) -> None:
        self.result_choice = "merge_into_b"
        self.selected_fields = self._get_selected_fields()
        self.accept()

    def _get_selected_fields(self) -> List[str]:
        pairs = [("srcaddr", self._cb_src), ("dstaddr", self._cb_dst), ("service", self._cb_svc)]
        return [name for name, cb in pairs if cb.isChecked()]


