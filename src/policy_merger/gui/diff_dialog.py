from __future__ import annotations

from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from ..models import PolicyRule


class DiffDialog(QDialog):
    def __init__(self, rule_a: PolicyRule, rule_b: PolicyRule, columns: List[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rule Diff")
        self.rule_a = rule_a
        self.rule_b = rule_b
        self.columns = columns

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"A from {rule_a.source_fortigate}: {rule_a.raw.get('name','')}", self))
        layout.addWidget(QLabel(f"B from {rule_b.source_fortigate}: {rule_b.raw.get('name','')}", self))

        table = QTableWidget(self)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Field", "A", "B"])
        rows: List[Tuple[str, str, str]] = []
        for field in self.columns:
            a_val = (rule_a.raw.get(field, "") or "").strip()
            b_val = (rule_b.raw.get(field, "") or "").strip()
            rows.append((field, a_val, b_val))
        table.setRowCount(len(rows))

        diff_color = QColor(255, 235, 205)  # light peach for differences
        for r, (field, a_val, b_val) in enumerate(rows):
            item_field = QTableWidgetItem(field)
            item_a = QTableWidgetItem(a_val)
            item_b = QTableWidgetItem(b_val)
            if a_val != b_val:
                item_a.setBackground(diff_color)
                item_b.setBackground(diff_color)
            item_field.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_a.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_b.setFlags(Qt.ItemFlag.ItemIsEnabled)
            table.setItem(r, 0, item_field)
            table.setItem(r, 1, item_a)
            table.setItem(r, 2, item_b)
        table.resizeColumnsToContents()
        table.setAlternatingRowColors(True)
        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


