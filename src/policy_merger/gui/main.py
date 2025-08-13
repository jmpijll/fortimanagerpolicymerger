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
)
from PyQt6.QtGui import QAction

from ..csv_loader import read_policy_csv
from .models import PolicyTableModel


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


def run() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1200, 700)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()


