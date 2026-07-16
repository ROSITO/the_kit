"""Éditeur Qt minimal — liste de nœuds, presets, export JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from the_kit.designer.presets import PRESETS_DIR, list_presets, load_preset
from the_kit.protocol.validator import ProtocolValidationError, validate_protocol
from the_kit.protocol.loader import load_protocol


def run_designer(protocol_path: str | Path | None = None) -> int:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QApplication,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    class DesignerWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("The Kit — Concepteur (Phase 2)")
            self.resize(700, 500)
            self._path: Path | None = Path(protocol_path).resolve() if protocol_path else None
            self._data: dict = {"protocol_version": "1.0", "name": "nouveau", "loop": 1, "nodes": []}

            if self._path and self._path.exists():
                with self._path.open(encoding="utf-8") as f:
                    self._data = json.load(f)

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            self.path_label = QLabel(str(self._path or "Non enregistré"))
            layout.addWidget(self.path_label)
            self.list_widget = QListWidget()
            self._refresh_list()
            layout.addWidget(self.list_widget)

            row = QHBoxLayout()
            btn_preset = QPushButton("Charger preset…")
            btn_preset.clicked.connect(self._load_preset)
            btn_validate = QPushButton("Valider")
            btn_validate.clicked.connect(self._validate)
            btn_save = QPushButton("Enregistrer")
            btn_save.clicked.connect(self._save)
            row.addWidget(btn_preset)
            row.addWidget(btn_validate)
            row.addWidget(btn_save)
            layout.addLayout(row)

        def _refresh_list(self) -> None:
            self.list_widget.clear()
            for i, n in enumerate(self._data.get("nodes", [])):
                self.list_widget.addItem(
                    f"[{i}] {n.get('id', '?')} — {n.get('type')} ({n.get('engine', '?')})"
                )

        def _load_preset(self) -> None:
            presets = list_presets()
            if not presets:
                QMessageBox.warning(self, "Presets", f"Aucun preset dans {PRESETS_DIR}")
                return
            name, ok = QFileDialog.getOpenFileName(
                self,
                "Choisir un preset",
                str(PRESETS_DIR),
                "JSON (*.json)",
            )
            if not ok:
                return
            with open(ok, encoding="utf-8") as f:
                self._data = json.load(f)
            self._path = None
            self.path_label.setText("Preset chargé (non enregistré)")
            self._refresh_list()

        def _validate(self) -> None:
            import tempfile

            try:
                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
                    json.dump(self._data, tf, ensure_ascii=False, indent=2)
                    tmp = tf.name
                p = load_protocol(tmp)
                validate_protocol(p)
                QMessageBox.information(self, "Validation", f"OK — {len(p.nodes)} nœuds")
            except ProtocolValidationError as e:
                QMessageBox.critical(self, "Invalide", "\n".join(e.errors))
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

        def _save(self) -> None:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer protocole",
                str(self._path or "protocol.json"),
                "JSON (*.json)",
            )
            if not path:
                return
            self._path = Path(path)
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            self.path_label.setText(str(self._path))
            QMessageBox.information(self, "Enregistré", str(self._path))

    app = QApplication(sys.argv)
    win = DesignerWindow()
    win.show()
    return app.exec()
