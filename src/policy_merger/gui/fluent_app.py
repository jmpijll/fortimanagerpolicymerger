from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import List

from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    FluentIcon as FIF,
    setTheme,
    Theme,
    PrimaryPushButton,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox,
    QTableView,
    QDialog,
    QWidget,
)
from PyQt6.QtCore import Qt

from policy_merger.csv_loader import read_policy_csv
from policy_merger.diff_engine import find_similar_rules, deduplicate_identical_rules, group_similarity_suggestions
from policy_merger.merger import write_merged_csv, merge_fields
from policy_merger.models import PolicySet
from policy_merger.gui.models import PolicyTableModel
from policy_merger.gui.merge_dialog import MergeDialog
from policy_merger.gui.diff_dialog import DiffDialog
from policy_merger.logging_config import configure_logging


@dataclass
class AppState:
    policy_sets: List[PolicySet] = field(default_factory=list)
    model: PolicyTableModel = field(default_factory=PolicyTableModel)


class ImportPage(QFrame):
    def __init__(self, state: AppState, on_import_complete: callable | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.on_import_complete = on_import_complete
        self.setObjectName("Import")

        layout = QVBoxLayout(self)
        title = QLabel("Import FortiManager CSV Exports", self)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        open_btn = PrimaryPushButton("Open CSVs", self)
        open_btn.clicked.connect(self._open_files)
        self._status = QLabel("No files loaded", self)
        self._status.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(open_btn)
        layout.addWidget(self._status)

    def _open_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select FortiManager CSV exports",
            os.getcwd(),
            "CSV Files (*.csv)"
        )
        if not files:
            return
        try:
            policy_sets = [read_policy_csv(path) for path in files]
            # Auto-dedupe identical rules across all sets
            all_rules = [r for ps in policy_sets for r in ps.rules]
            unique_rules, removed = deduplicate_identical_rules(all_rules)
            # Build a synthetic set for display with union columns preserved from first file
            display_columns = policy_sets[0].columns if policy_sets and policy_sets[0].columns else []
            ps_display = PolicySet(source_fortigate="MERGED", columns=display_columns)
            for r in unique_rules:
                ps_display.add_rule(r.raw)
            self.state.policy_sets = [ps_display]
            self.state.model.set_policy_sets(self.state.policy_sets)
            total_rules = len(unique_rules)
            dedupe_note = f" (removed {removed} duplicate rule(s))" if removed else ""
            self._status.setText(f"Loaded {total_rules} unique rules from {len(files)} files{dedupe_note}")
            if self.on_import_complete:
                self.on_import_complete()
            QMessageBox.information(self, "Loaded", f"Loaded {total_rules} unique rules from {len(files)} files{dedupe_note}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class ReviewPage(QFrame):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.setObjectName("Review")

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Review & Resolve", self)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._btn_refresh = PrimaryPushButton("Refresh Suggestions", self)
        self._btn_resolve = PrimaryPushButton("Resolve Suggestions", self)
        self._btn_compare = PrimaryPushButton("Compare Selected", self)
        self._btn_refresh.clicked.connect(self._refresh_suggestions)
        self._btn_resolve.clicked.connect(self._resolve_suggestions)
        self._btn_compare.clicked.connect(self._compare_selected)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self._btn_refresh)
        header.addWidget(self._btn_compare)
        header.addWidget(self._btn_resolve)

        self._table = QTableView(self)
        self._table.setModel(self.state.model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)

        layout.addLayout(header)
        layout.addWidget(self._table)

        self._current_groups = {}

    def _refresh_suggestions(self) -> None:
        if self.state.model.rowCount() == 0:
            QMessageBox.information(self, "No data", "Load CSVs first")
            return
        self._current_groups = group_similarity_suggestions(self.state.model._rules)
        total_pairs = sum(len(v) for v in self._current_groups.values())
        QMessageBox.information(self, "Suggestions", f"Found {total_pairs} similar pair(s) across {len(self._current_groups)} group(s)")

    def _compare_selected(self) -> None:
        sel = self._table.selectionModel().selectedRows()
        if len(sel) != 2:
            QMessageBox.information(self, "Select two rows", "Please select exactly two rows to compare")
            return
        rows = [idx.row() for idx in sel]
        try:
            rules = self.state.model._rules  # type: ignore[attr-defined]
            columns = self.state.model._columns  # type: ignore[attr-defined]
            rule_a = rules[rows[0]]
            rule_b = rules[rows[1]]
            dlg = DiffDialog(rule_a, rule_b, columns, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _resolve_suggestions(self) -> None:
        if self.state.model.rowCount() == 0:
            QMessageBox.information(self, "No data", "Load CSVs first")
            return
        suggestions = find_similar_rules(self.state.model._rules)  # type: ignore[attr-defined]
        if not suggestions:
            QMessageBox.information(self, "No suggestions", "No similar rules detected with current heuristic")
            return
        removed_ids = set()
        for s in suggestions:
            if id(s.rule_a) in removed_ids or id(s.rule_b) in removed_ids:
                continue
            dlg = MergeDialog(s.rule_a, s.rule_b, self)
            if dlg.exec() != QDialog.Accepted:  # type: ignore[name-defined]
                continue
            choice = dlg.result_choice
            if choice == "keep_a":
                removed_ids.add(id(s.rule_b))
            elif choice == "keep_b":
                removed_ids.add(id(s.rule_a))
            elif choice == "keep_both":
                name_b = s.rule_b.raw.get("name", "").strip()
                s.rule_b.raw["name"] = f"{name_b}-from-{s.rule_b.source_fortigate}" if name_b else f"rule-from-{s.rule_b.source_fortigate}"
            elif choice == "merge_into_a":
                merged = merge_fields(s.rule_a, s.rule_b, fields=("srcaddr", "dstaddr", "service"))
                s.rule_a.raw.update(merged)
                removed_ids.add(id(s.rule_b))
            elif choice == "merge_into_b":
                merged = merge_fields(s.rule_b, s.rule_a, fields=("srcaddr", "dstaddr", "service"))
                s.rule_b.raw.update(merged)
                removed_ids.add(id(s.rule_a))
        if removed_ids:
            remaining = [r for r in self.state.model._rules if id(r) not in removed_ids]  # type: ignore[attr-defined]
            from policy_merger.models import PolicySet
            ps = PolicySet(source_fortigate="MERGED", columns=self.state.model._columns)  # type: ignore[attr-defined]
            for r in remaining:
                ps.add_rule(r.raw)
            self.state.model.set_policy_sets([ps])


class ExportPage(QFrame):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.setObjectName("Export")

        layout = QVBoxLayout(self)
        title = QLabel("Export Merged Policies", self)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        export_btn = PrimaryPushButton("Save merged CSV", self)
        export_btn.clicked.connect(self._export_csv)
        self._status = QLabel("", self)
        self._status.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(export_btn)
        layout.addWidget(self._status)

    def _export_csv(self) -> None:
        if self.state.model.rowCount() == 0:
            QMessageBox.information(self, "Nothing to export", "Load CSVs first")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Save merged CSV", os.getcwd(), "CSV Files (*.csv)")
        if not out:
            return
        rules = self.state.model._rules  # type: ignore[attr-defined]
        try:
            write_merged_csv(out, rules, preferred_columns=self.state.model._columns)  # type: ignore[attr-defined]
            self._status.setText(f"Wrote {len(rules)} rules to {out}")
            QMessageBox.information(self, "Exported", f"Wrote {len(rules)} rules to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class FluentMainWindow(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Policy Merger")
        self.state = AppState()

        # Pages
        self.importPage = ImportPage(self.state, on_import_complete=self._goto_review, parent=self)
        self.reviewPage = ReviewPage(self.state, parent=self)
        self.exportPage = ExportPage(self.state, parent=self)

        self._initNavigation()
        self._initWindow()

    def _goto_review(self) -> None:
        # Switch to Review page after successful import
        self.switchTo(self.reviewPage)

    def _initNavigation(self) -> None:
        self.addSubInterface(self.importPage, FIF.FOLDER, "Import")
        self.addSubInterface(self.reviewPage, FIF.FOLDER, "Review")
        self.addSubInterface(self.exportPage, FIF.SAVE, "Export", NavigationItemPosition.BOTTOM)

    def _initWindow(self) -> None:
        self.resize(1200, 800)


def run() -> None:
    configure_logging()
    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)
    w = FluentMainWindow()
    w.show()
    code = app.exec()
    os._exit(code)


if __name__ == "__main__":
    run()


