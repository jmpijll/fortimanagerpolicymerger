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
    setThemeColor,
    PrimaryPushButton,
    PillPushButton,
    InfoBar,
    InfoBarIcon,
    InfoBarPosition,
    TeachingTip,
    TeachingTipTailPosition,
    TogglePushButton,
    ColorDialog,
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
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices

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

        # Quick tip for first-time users
        TeachingTip.create(
            target=open_btn,
            icon=InfoBarIcon.INFORMATION,
            title='Start here',
            content='Click to select multiple FortiManager CSV exports to begin.',
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            duration=3000,
            parent=self
        )

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
        self._btn_toggle_columns = TogglePushButton("Compact Columns", self)
        self._btn_toggle_columns.setChecked(True)
        self._btn_toggle_theme = PrimaryPushButton("Toggle Theme", self)
        self._btn_toggle_details = TogglePushButton("Show Details", self)
        self._btn_toggle_details.setChecked(True)
        self._btn_system_accent = PrimaryPushButton("System Accent", self)
        self._btn_pick_accent = PrimaryPushButton("Pick Accent", self)
        self._btn_refresh.clicked.connect(self._refresh_suggestions)
        self._btn_resolve.clicked.connect(self._resolve_suggestions)
        self._btn_compare.clicked.connect(self._compare_selected)
        self._btn_toggle_columns.toggled.connect(self._on_toggle_columns)
        self._btn_toggle_theme.clicked.connect(self._toggle_theme)
        self._btn_toggle_details.toggled.connect(self._on_toggle_details)
        self._btn_system_accent.clicked.connect(self._apply_system_accent)
        self._btn_pick_accent.clicked.connect(self._pick_accent)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self._btn_toggle_columns)
        header.addWidget(self._btn_toggle_details)
        header.addWidget(self._btn_toggle_theme)
        header.addWidget(self._btn_system_accent)
        header.addWidget(self._btn_pick_accent)
        header.addWidget(self._btn_refresh)
        header.addWidget(self._btn_compare)
        header.addWidget(self._btn_resolve)

        # Content area: table + details (left) + group actions (right)
        content = QHBoxLayout()
        self._table = QTableView(self)
        self._table.setModel(self.state.model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)

        # Details panel for selected rule
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)
        left.addWidget(self._table)
        self._details = QTableWidget(self)
        self._details.setColumnCount(2)
        self._details.setHorizontalHeaderLabels(["Field", "Value"])
        left.addWidget(self._details)

        # Right panel: suggestions and batch actions
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)
        right.addWidget(QLabel("Suggestion Groups", self))
        self._groups_list = QListWidget(self)
        right.addWidget(self._groups_list)

        right.addWidget(QLabel("Group Details", self))
        self._pairs_list = QListWidget(self)
        right.addWidget(self._pairs_list)

        # Per-pair actions
        self._btn_open_diff = QPushButton("Open Diff", self)
        self._btn_open_diff.clicked.connect(self._open_selected_pair_diff)
        right.addWidget(self._btn_open_diff)

        # Diff chips container
        right.addWidget(QLabel("Differing fields", self))
        self._chip_frame = QFrame(self)
        self._chip_layout = QHBoxLayout(self._chip_frame)
        self._chip_layout.setContentsMargins(0, 0, 0, 0)
        self._chip_layout.setSpacing(6)
        right.addWidget(self._chip_frame)

        self._btn_keep_a = QPushButton("Keep A (batch)", self)
        self._btn_keep_b = QPushButton("Keep B (batch)", self)
        self._btn_keep_both = QPushButton("Keep both (rename B)", self)
        self._btn_merge_a = QPushButton("Merge into A (batch)", self)
        self._btn_merge_b = QPushButton("Merge into B (batch)", self)
        self._btn_keep_a.clicked.connect(lambda: self._apply_batch_action("keep_a"))
        self._btn_keep_b.clicked.connect(lambda: self._apply_batch_action("keep_b"))
        self._btn_keep_both.clicked.connect(lambda: self._apply_batch_action("keep_both"))
        self._btn_merge_a.clicked.connect(lambda: self._apply_batch_action("merge_into_a"))
        self._btn_merge_b.clicked.connect(lambda: self._apply_batch_action("merge_into_b"))
        right.addWidget(self._btn_keep_a)
        right.addWidget(self._btn_keep_b)
        right.addWidget(self._btn_keep_both)
        right.addWidget(self._btn_merge_a)
        right.addWidget(self._btn_merge_b)

        left_container = QFrame(self)
        left_container.setLayout(left)
        content.addWidget(left_container, 3)
        right_container = QFrame(self)
        right_container.setLayout(right)
        content.addWidget(right_container, 1)

        layout.addLayout(header)
        layout.addLayout(content)

        self._current_groups = {}
        self._group_keys: List[tuple] = []
        self._current_group_index: int = -1
        self._current_pair_index: int = -1
        self._is_dark: bool = False

        # Wire selection changes
        self._groups_list.currentRowChanged.connect(self._on_group_selected)
        self._pairs_list.currentRowChanged.connect(self._on_pair_selected)
        self._table.selectionModel().selectionChanged.connect(self._update_details_from_selected_row)
        # Set compact default columns (identity fields) for review
        identity_cols = [
            "name",
            "srcintf",
            "dstintf",
            "srcaddr",
            "dstaddr",
            "service",
            "schedule",
            "action",
            "nat",
        ]
        available = self.state.model.all_columns()
        compact = [c for c in identity_cols if c in available]
        if compact:
            self.state.model.set_display_columns(compact)
        self._update_details_from_selected_row()

    def _on_toggle_details(self, checked: bool) -> None:
        self._details.setVisible(checked)

    def _apply_system_accent(self) -> None:
        try:
            if sys.platform in ["win32", "darwin"]:
                from qframelesswindow.utils import getSystemAccentColor  # type: ignore
                setThemeColor(getSystemAccentColor(), save=False)
                InfoBar.success(
                    title='Accent applied',
                    content='Using system accent color',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=2000,
                    parent=self
                )
            else:
                InfoBar.info(
                    title='Not supported',
                    content='System accent only on Windows/macOS',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=3000,
                    parent=self
                )
        except Exception as e:
            InfoBar.warning(
                title='Accent failed',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4000,
                parent=self
            )

    def _pick_accent(self) -> None:
        try:
            from PyQt6.QtGui import QColor
            dlg = ColorDialog(QColor(0, 120, 215), "Choose Accent Color", self, enableAlpha=False)
            if dlg.exec():
                color = dlg.color()
                setThemeColor(color, save=False)
                InfoBar.success(
                    title='Accent applied',
                    content=color.name(),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            InfoBar.warning(
                title='Accent failed',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4000,
                parent=self
            )

    def _refresh_suggestions(self) -> None:
        if self.state.model.rowCount() == 0:
            QMessageBox.information(self, "No data", "Load CSVs first")
            return
        self._current_groups = group_similarity_suggestions(self.state.model._rules)
        self._group_keys = list(self._current_groups.keys())
        self._groups_list.clear()
        total_pairs = 0
        for idx, key in enumerate(self._group_keys, start=1):
            suggestions = self._current_groups[key]
            total_pairs += len(suggestions)
            # Collect differing fields across group
            fields = set()
            for s in suggestions:
                fields.update(s.field_diffs.keys())
            field_str = ", ".join(sorted(fields)) if fields else "(identical)"
            self._groups_list.addItem(f"Group {idx}: {len(suggestions)} pair(s) | diffs: {field_str}")
        InfoBar.info(
            title='Suggestions updated',
            content=f"Found {total_pairs} similar pair(s) across {len(self._current_groups)} group(s)",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self
        )
        # Teaching tip to guide usage
        TeachingTip.create(
            target=self._groups_list,
            icon=InfoBarIcon.INFORMATION,
            title='How to use',
            content='Select a group to see its pairs, then select a pair to view differing fields. Use batch actions for the whole group.',
            isClosable=True,
            tailPosition=TeachingTipTailPosition.RIGHT,
            duration=4000,
            parent=self
        )

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
                # Use selected fields from dialog if provided
                fields = tuple(dlg.selected_fields) if getattr(dlg, 'selected_fields', None) else ("srcaddr", "dstaddr", "service")
                merged = merge_fields(s.rule_a, s.rule_b, fields=fields)
                s.rule_a.raw.update(merged)
                removed_ids.add(id(s.rule_b))
            elif choice == "merge_into_b":
                fields = tuple(dlg.selected_fields) if getattr(dlg, 'selected_fields', None) else ("srcaddr", "dstaddr", "service")
                merged = merge_fields(s.rule_b, s.rule_a, fields=fields)
                s.rule_b.raw.update(merged)
                removed_ids.add(id(s.rule_a))
        if removed_ids:
            remaining = [r for r in self.state.model._rules if id(r) not in removed_ids]  # type: ignore[attr-defined]
            from policy_merger.models import PolicySet
            ps = PolicySet(source_fortigate="MERGED", columns=self.state.model._columns)  # type: ignore[attr-defined]
            for r in remaining:
                ps.add_rule(r.raw)
            self.state.model.set_policy_sets([ps])
            # refresh pairs/chips view
            self._on_group_selected(self._groups_list.currentRow())

    def _on_group_selected(self, row: int) -> None:
        self._current_group_index = row
        self._pairs_list.clear()
        self._clear_chips()
        if row < 0 or row >= len(self._group_keys):
            return
        key = self._group_keys[row]
        suggestions = self._current_groups.get(key, [])
        for i, s in enumerate(suggestions, start=1):
            a_name = (s.rule_a.raw.get('name', '') or '').strip()
            b_name = (s.rule_b.raw.get('name', '') or '').strip()
            a_src = s.rule_a.source_fortigate
            b_src = s.rule_b.source_fortigate
            fields = ','.join(sorted(s.field_diffs.keys())) if s.field_diffs else '(identical)'
            self._pairs_list.addItem(f"Pair {i}: A:{a_name} ({a_src}) vs B:{b_name} ({b_src}) | diffs: {fields}")

    def _on_pair_selected(self, row: int) -> None:
        self._current_pair_index = row
        self._clear_chips()
        if self._current_group_index < 0 or self._current_group_index >= len(self._group_keys):
            return
        key = self._group_keys[self._current_group_index]
        suggestions = self._current_groups.get(key, [])
        if row < 0 or row >= len(suggestions):
            return
        s = suggestions[row]
        fields = sorted(s.field_diffs.keys()) if s.field_diffs else []
        if not fields:
            chip = PillPushButton('identical', self._chip_frame)
            chip.setEnabled(False)
            self._chip_layout.addWidget(chip)
            return
        for f in fields:
            chip = PillPushButton(f, self._chip_frame)
            chip.setEnabled(False)
            self._chip_layout.addWidget(chip)

    def _on_toggle_columns(self, checked: bool) -> None:
        if checked:
            identity_cols = [
                "name",
                "srcintf",
                "dstintf",
                "srcaddr",
                "dstaddr",
                "service",
                "schedule",
                "action",
                "nat",
            ]
            available = self.state.model.all_columns()
            compact = [c for c in identity_cols if c in available]
            self.state.model.set_display_columns(compact)
        else:
            self.state.model.set_display_columns(None)
        self._update_details_from_selected_row()

    def _update_details_from_selected_row(self) -> None:
        # Show details for first selected row
        sel = self._table.selectionModel().selectedRows()
        if not sel:
            self._details.clearContents()
            self._details.setRowCount(0)
            return
        row = sel[0].row()
        try:
            rule = self.state.model._rules[row]  # type: ignore[attr-defined]
            columns = self.state.model._columns  # type: ignore[attr-defined]
            self._details.setRowCount(len(columns))
            for i, col in enumerate(columns):
                item_field = QTableWidgetItem(col)
                val = (rule.raw.get(col, "") or "").strip()
                item_val = QTableWidgetItem(val)
                item_field.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item_val.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._details.setItem(i, 0, item_field)
                self._details.setItem(i, 1, item_val)
            self._details.resizeColumnsToContents()
        except Exception:
            pass

    def _toggle_theme(self) -> None:
        # Simple toggle between light and dark themes
        self._is_dark = not self._is_dark
        setTheme(Theme.DARK if self._is_dark else Theme.LIGHT)

    def _clear_chips(self) -> None:
        while self._chip_layout.count():
            item = self._chip_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _open_selected_pair_diff(self) -> None:
        if self._current_group_index < 0 or self._current_group_index >= len(self._group_keys):
            return
        key = self._group_keys[self._current_group_index]
        suggestions = self._current_groups.get(key, [])
        if self._current_pair_index < 0 or self._current_pair_index >= len(suggestions):
            return
        s = suggestions[self._current_pair_index]
        columns = self.state.model._columns  # type: ignore[attr-defined]
        dlg = DiffDialog(s.rule_a, s.rule_b, columns, self)
        dlg.exec()

    def _apply_batch_action(self, action: str) -> None:
        if self._groups_list.currentRow() < 0 or not self._group_keys:
            QMessageBox.information(self, "Select group", "Please select a suggestion group first")
            return
        key = self._group_keys[self._groups_list.currentRow()]
        suggestions = self._current_groups.get(key, [])
        if not suggestions:
            QMessageBox.information(self, "Empty group", "No suggestions in the selected group")
            return
        if action not in {"keep_a", "keep_b", "keep_both", "merge_into_a", "merge_into_b"}:
            QMessageBox.warning(self, "Unknown action", action)
            return
        confirm = QMessageBox.question(self, "Apply batch", f"Apply '{action}' to {len(suggestions)} pair(s) in this group?" )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        removed_ids = set()
        for s in suggestions:
            if id(s.rule_a) in removed_ids or id(s.rule_b) in removed_ids:
                continue
            if action == "keep_a":
                removed_ids.add(id(s.rule_b))
            elif action == "keep_b":
                removed_ids.add(id(s.rule_a))
            elif action == "keep_both":
                name_b = s.rule_b.raw.get("name", "").strip()
                s.rule_b.raw["name"] = f"{name_b}-from-{s.rule_b.source_fortigate}" if name_b else f"rule-from-{s.rule_b.source_fortigate}"
            elif action == "merge_into_a":
                merged = merge_fields(s.rule_a, s.rule_b, fields=("srcaddr", "dstaddr", "service"))
                s.rule_a.raw.update(merged)
                removed_ids.add(id(s.rule_b))
            elif action == "merge_into_b":
                merged = merge_fields(s.rule_b, s.rule_a, fields=("srcaddr", "dstaddr", "service"))
                s.rule_b.raw.update(merged)
                removed_ids.add(id(s.rule_a))
        if removed_ids:
            remaining = [r for r in self.state.model._rules if id(r) not in removed_ids]  # type: ignore[attr-defined]
            ps = PolicySet(source_fortigate="MERGED", columns=self.state.model._columns)  # type: ignore[attr-defined]
            for r in remaining:
                ps.add_rule(r.raw)
            self.state.model.set_policy_sets([ps])
            # refresh suggestions after changes
            self._refresh_suggestions()


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
        self._btn_open_logs = PrimaryPushButton("Open Logs Folder", self)
        self._btn_open_logs.clicked.connect(self._open_logs)

        layout.addWidget(title)
        layout.addWidget(export_btn)
        layout.addWidget(self._btn_open_logs)
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

    def _open_logs(self) -> None:
        try:
            from PyQt6.QtCore import QStandardPaths
            base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation) or ""
            if base_dir:
                QDesktopServices.openUrl(QUrl.fromLocalFile(base_dir))
            else:
                QMessageBox.information(self, "Logs", "App data location not available")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class AboutPage(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("About")
        layout = QVBoxLayout(self)
        title = QLabel("About Policy Merger", self)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        try:
            from policy_merger import __version__
        except Exception:
            __version__ = "dev"
        ver = QLabel(f"Version: {__version__}", self)
        ver.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        layout.addWidget(ver)


class FluentMainWindow(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Policy Merger")
        self.state = AppState()

        # Pages
        self.importPage = ImportPage(self.state, on_import_complete=self._goto_review, parent=self)
        self.reviewPage = ReviewPage(self.state, parent=self)
        self.exportPage = ExportPage(self.state, parent=self)
        self.aboutPage = AboutPage(parent=self)

        self._initNavigation()
        self._initWindow()

    def _goto_review(self) -> None:
        # Switch to Review page after successful import
        self.switchTo(self.reviewPage)

    def _initNavigation(self) -> None:
        self.addSubInterface(self.importPage, FIF.FOLDER, "Import")
        self.addSubInterface(self.reviewPage, FIF.FOLDER, "Review")
        self.addSubInterface(self.exportPage, FIF.SAVE, "Export", NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.aboutPage, FIF.HELP, "About", NavigationItemPosition.BOTTOM)

    def _initWindow(self) -> None:
        self.resize(1200, 800)
        # Window icon (bundled with QFluentWidgets resources)
        try:
            self.setWindowIcon(QIcon(':/qfluentwidgets/images/logo.png'))
        except Exception:
            pass
        # Navigation sizing and behavior
        try:
            self.navigationInterface.setMinimumExpandWidth(900)
            self.navigationInterface.setExpandWidth(300)
            self.navigationInterface.setCollapsible(False)
        except Exception:
            pass


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


