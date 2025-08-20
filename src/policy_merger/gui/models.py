from __future__ import annotations

from typing import List

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant

from ..models import PolicyRule, PolicySet


class PolicyTableModel(QAbstractTableModel):
    def __init__(self, policy_sets: List[PolicySet] | None = None) -> None:
        super().__init__()
        self._rules: List[PolicyRule] = []
        self._columns: List[str] = []
        self._display_columns: List[str] | None = None
        self._editable: bool = False
        if policy_sets:
            self.set_policy_sets(policy_sets)

    def set_policy_sets(self, policy_sets: List[PolicySet]) -> None:
        self.beginResetModel()
        self._rules = [r for ps in policy_sets for r in ps.rules]
        # Derive columns from first set
        if policy_sets and policy_sets[0].columns:
            self._columns = list(policy_sets[0].columns)
        elif self._rules:
            self._columns = list(self._rules[0].raw.keys())
        else:
            self._columns = []
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._rules)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        cols = self._display_columns if self._display_columns is not None else self._columns
        return len(cols)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> QVariant:  # type: ignore[override]
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return QVariant()
        rule = self._rules[index.row()]
        cols = self._display_columns if self._display_columns is not None else self._columns
        col = cols[index.column()]
        value = rule.raw.get(col, "")
        if role == Qt.ItemDataRole.ToolTipRole and col != "name":
            return f"{value} (from {rule.source_fortigate})"
        return value

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):  # type: ignore[override]
        if role != Qt.ItemDataRole.DisplayRole:
            return QVariant()
        if orientation == Qt.Orientation.Horizontal:
            cols = self._display_columns if self._display_columns is not None else self._columns
            if 0 <= section < len(cols):
                return cols[section]
        else:
            return section + 1
        return QVariant()

    def flags(self, index: QModelIndex):  # type: ignore[override]
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if self._editable:
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole):  # type: ignore[override]
        if not index.isValid() or role != Qt.ItemDataRole.EditRole or not self._editable:
            return False
        row = index.row()
        col_idx = index.column()
        cols = self._display_columns if self._display_columns is not None else self._columns
        if row < 0 or row >= len(self._rules) or col_idx < 0 or col_idx >= len(cols):
            return False
        col = cols[col_idx]
        self._rules[row].raw[col] = str(value)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
        return True

    def set_display_columns(self, columns: List[str] | None) -> None:
        self.beginResetModel()
        self._display_columns = list(columns) if columns is not None else None
        self.endResetModel()

    def all_columns(self) -> List[str]:
        return list(self._columns)

    def set_editable(self, editable: bool) -> None:
        if self._editable != editable:
            self._editable = editable
            # emit layoutChanged to update flags
            self.layoutChanged.emit()


