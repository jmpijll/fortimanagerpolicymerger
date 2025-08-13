from __future__ import annotations

import os
import sys
from typing import List

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QTableView,
    QToolBar,
    QMessageBox,
    QDialog,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QStandardPaths

from policy_merger.csv_loader import read_policy_csv
from policy_merger.diff_engine import find_similar_rules
from policy_merger.merger import write_merged_csv, merge_fields
from policy_merger.gui.models import PolicyTableModel
from policy_merger.gui.merge_dialog import MergeDialog
from policy_merger.gui.diff_dialog import DiffDialog
from policy_merger.logging_config import configure_logging


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Policy Merger")

        self._table = QTableView(self)
        self.setCentralWidget(self._table)

        self._model = PolicyTableModel()
        self._table.setModel(self._model)

        self._create_toolbar()

    def _create_toolbar(self) -> None:
        tb = QToolBar("Main")
        self.addToolBar(tb)

        open_action = QAction("Open CSVs", self)
        open_action.triggered.connect(self._open_files)
        tb.addAction(open_action)

        export_action = QAction("Export Merged CSV", self)
        export_action.triggered.connect(self._export_csv)
        tb.addAction(export_action)

        resolve_action = QAction("Resolve Suggestions", self)
        resolve_action.triggered.connect(self._resolve_suggestions)
        tb.addAction(resolve_action)

        compare_action = QAction("Compare Selected", self)
        compare_action.triggered.connect(self._compare_selected)
        tb.addAction(compare_action)

        save_session_action = QAction("Save Session", self)
        save_session_action.triggered.connect(self._save_session)
        tb.addAction(save_session_action)

        load_session_action = QAction("Load Session", self)
        load_session_action.triggered.connect(self._load_session)
        tb.addAction(load_session_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._about)
        tb.addAction(about_action)

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
            self._model.set_policy_sets(policy_sets)
            QMessageBox.information(self, "Loaded", f"Loaded {sum(len(ps.rules) for ps in policy_sets)} rules from {len(files)} files")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _compare_selected(self) -> None:
        sel = self._table.selectionModel().selectedRows()
        if len(sel) != 2:
            QMessageBox.information(self, "Select two rows", "Please select exactly two rows to compare")
            return
        rows = [idx.row() for idx in sel]
        try:
            rule_a = self._model._rules[rows[0]]
            rule_b = self._model._rules[rows[1]]
            dlg = DiffDialog(rule_a, rule_b, self._model._columns, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _save_session(self) -> None:
        if self._model.rowCount() == 0:
            QMessageBox.information(self, "No data", "Nothing to save")
            return
        import json
        rows = [r.raw for r in self._model._rules]
        data = {
            "version": 1,
            "columns": self._model._columns,
            "rules": rows,
        }
        base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation) or ""
        default_path = base_dir + "/session.json"
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save Session", default_path, "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            # ensure dir exists
            import os, pathlib
            pathlib.Path(os.path.dirname(path) or ".").mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Saved", f"Session saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _load_session(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cols = data.get("columns", [])
            rules = data.get("rules", [])
            from policy_merger.models import PolicySet
            ps = PolicySet(source_fortigate="SESSION", columns=cols)
            for row in rules:
                ps.add_rule(row)
            self._model.set_policy_sets([ps])
            QMessageBox.information(self, "Loaded", f"Loaded session from {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _about(self) -> None:
        try:
            from policy_merger import __version__
        except Exception:
            __version__ = "dev"
        QMessageBox.information(self, "About", f"Policy Merger\nVersion {__version__}")

    def _export_csv(self) -> None:
        if self._model.rowCount() == 0:
            QMessageBox.information(self, "Nothing to export", "Load CSVs first")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Save merged CSV", os.getcwd(), "CSV Files (*.csv)")
        if not out:
            return
        # Build list from model's internal data
        rules = self._model._rules  # read-only usage here
        try:
            write_merged_csv(out, rules, preferred_columns=self._model._columns)
            QMessageBox.information(self, "Exported", f"Wrote {len(rules)} rules to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _resolve_suggestions(self) -> None:
        if self._model.rowCount() == 0:
            QMessageBox.information(self, "No data", "Load CSVs first")
            return
        suggestions = find_similar_rules(self._model._rules)
        if not suggestions:
            QMessageBox.information(self, "No suggestions", "No similar rules detected with current heuristic")
            return
        # Iterate suggestions and prompt user
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
                # rename second
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
            # Rebuild model rules excluding removed
            remaining = [r for r in self._model._rules if id(r) not in removed_ids]
            from policy_merger.models import PolicySet
            ps = PolicySet(source_fortigate="MERGED", columns=self._model._columns)
            for r in remaining:
                ps.add_rule(r.raw)
            self._model.set_policy_sets([ps])


def run() -> None:
    configure_logging()
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1200, 700)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()


