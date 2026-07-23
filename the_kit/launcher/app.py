"""Lanceur Qt — choisir un protocol.json et exécuter une session."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from the_kit.protocol.validator import ProtocolValidationError, validate_protocol_file


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _python_executable() -> str:
    """Évite pythonw.exe sous Windows (pas de fenêtre SDL pour pygame)."""
    exe = sys.executable
    if sys.platform == "win32" and exe.lower().endswith("pythonw.exe"):
        candidate = Path(exe).with_name("python.exe")
        if candidate.is_file():
            return str(candidate)
    return exe


def _subprocess_environment():
    from PyQt6.QtCore import QProcessEnvironment

    env = QProcessEnvironment.systemEnvironment()
    for key, value in os.environ.items():
        env.insert(key, value)
    env.insert("PYTHONUNBUFFERED", "1")
    if sys.platform == "win32":
        env.insert("SDL_VIDEODRIVER", "windows")
    return env


def run_launcher() -> int:
    from PyQt6.QtCore import QProcess, Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    class LauncherWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("The Kit — Lanceur")
            self.resize(720, 520)
            self._process: QProcess | None = None
            self._root = _project_root()

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)

            intro = QLabel(
                "Sélectionnez un protocole et lancez une session participant.\n"
                "L'exécution s'effectue dans un processus séparé (fenêtres stimuli)."
            )
            intro.setWordWrap(True)
            layout.addWidget(intro)

            form_box = QGroupBox("Session")
            form = QFormLayout(form_box)

            proto_row = QHBoxLayout()
            self.protocol_edit = QLineEdit()
            self.protocol_edit.setPlaceholderText("Chemin vers protocol.json")
            self.protocol_edit.textChanged.connect(self._on_protocol_changed)
            btn_browse = QPushButton("Parcourir…")
            btn_browse.clicked.connect(self._browse_protocol)
            proto_row.addWidget(self.protocol_edit, stretch=1)
            proto_row.addWidget(btn_browse)
            form.addRow("Protocole :", proto_row)

            self.protocol_info = QLabel("")
            self.protocol_info.setStyleSheet("color: #555;")
            form.addRow("", self.protocol_info)

            self.subject_edit = QLineEdit()
            self.subject_edit.setPlaceholderText("ex. S001")
            form.addRow("Participant :", self.subject_edit)

            opts_row = QHBoxLayout()
            self.dry_run_cb = QCheckBox("Dry-run")
            self.dry_run_cb.setToolTip("Simuler NI / triggers sans matériel")
            self.check_media_cb = QCheckBox("Vérifier médias")
            opts_row.addWidget(self.dry_run_cb)
            opts_row.addWidget(self.check_media_cb)
            opts_row.addStretch()
            form.addRow("Options :", opts_row)

            layout.addWidget(form_box)

            btn_row = QHBoxLayout()
            self.btn_validate = QPushButton("Valider")
            self.btn_validate.clicked.connect(self._validate)
            self.btn_run = QPushButton("Lancer")
            self.btn_run.setDefault(True)
            self.btn_run.clicked.connect(self._run)
            self.btn_run.setEnabled(False)
            self.btn_stop = QPushButton("Arrêter")
            self.btn_stop.clicked.connect(self._stop)
            self.btn_stop.setEnabled(False)
            btn_row.addWidget(self.btn_validate)
            btn_row.addStretch()
            btn_row.addWidget(self.btn_stop)
            btn_row.addWidget(self.btn_run)
            layout.addLayout(btn_row)

            log_box = QGroupBox("Journal")
            log_layout = QVBoxLayout(log_box)
            self.log_view = QTextEdit()
            self.log_view.setReadOnly(True)
            self.log_view.setFont(QFont("Menlo", 11))
            log_layout.addWidget(self.log_view)
            layout.addWidget(log_box, stretch=1)

        def _append_log(self, text: str) -> None:
            self.log_view.moveCursor(self.log_view.textCursor().MoveOperation.End)
            self.log_view.insertPlainText(text)
            self.log_view.moveCursor(self.log_view.textCursor().MoveOperation.End)

        def _browse_protocol(self) -> None:
            start = self.protocol_edit.text().strip() or str(self._root / "examples")
            path, ok = QFileDialog.getOpenFileName(
                self,
                "Choisir un protocole",
                start,
                "Protocole JSON (*.json);;Tous (*.*)",
            )
            if ok and path:
                self.protocol_edit.setText(path)

        def _on_protocol_changed(self) -> None:
            path = self.protocol_edit.text().strip()
            self.btn_run.setEnabled(bool(path))
            self.protocol_info.setText("")
            if not path:
                return
            p = Path(path)
            if not p.is_file():
                self.protocol_info.setText("Fichier introuvable")
                self.protocol_info.setStyleSheet("color: #b00020;")
                return
            try:
                protocol = validate_protocol_file(p, check_media=False)
                self.protocol_info.setText(
                    f"OK — {protocol.name} · {len(protocol.nodes)} nœuds · v{protocol.protocol_version}"
                )
                self.protocol_info.setStyleSheet("color: #2e7d32;")
            except ProtocolValidationError as e:
                self.protocol_info.setText(e.errors[0] if e.errors else "Protocole invalide")
                self.protocol_info.setStyleSheet("color: #b00020;")
            except Exception as e:
                self.protocol_info.setText(str(e))
                self.protocol_info.setStyleSheet("color: #b00020;")

        def _validate(self) -> None:
            path = self.protocol_edit.text().strip()
            if not path:
                QMessageBox.warning(self, "Validation", "Choisissez un protocole.")
                return
            try:
                protocol = validate_protocol_file(
                    path,
                    check_media=self.check_media_cb.isChecked(),
                )
                QMessageBox.information(
                    self,
                    "Validation",
                    f"Protocole valide\n\n{protocol.name}\n{len(protocol.nodes)} nœuds",
                )
            except ProtocolValidationError as e:
                QMessageBox.critical(self, "Invalide", "\n".join(e.errors))
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

        def _set_running(self, running: bool) -> None:
            self.btn_run.setEnabled(not running and bool(self.protocol_edit.text().strip()))
            self.btn_validate.setEnabled(not running)
            self.btn_stop.setEnabled(running)
            self.protocol_edit.setEnabled(not running)
            self.subject_edit.setEnabled(not running)
            self.dry_run_cb.setEnabled(not running)
            self.check_media_cb.setEnabled(not running)

        def _run(self) -> None:
            path = self.protocol_edit.text().strip()
            if not path or not Path(path).is_file():
                QMessageBox.warning(self, "Lancement", "Protocole invalide ou absent.")
                return
            subject = self.subject_edit.text().strip() or "anonymous"

            args = [
                _python_executable(),
                "-m",
                "the_kit",
                "run",
                "-p",
                str(Path(path).resolve()),
                "-s",
                subject,
            ]
            if self.dry_run_cb.isChecked():
                args.append("--dry-run")
            if self.check_media_cb.isChecked():
                args.append("--check-media")
            # BIDS + rapport HTML : toujours exportés en fin de session (défaut CLI).

            self.log_view.clear()
            self._append_log(f"$ {' '.join(args)}\n\n")
            self._set_running(True)

            proc = QProcess(self)
            proc.setWorkingDirectory(str(self._root))
            proc.setProcessEnvironment(_subprocess_environment())
            proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            proc.readyReadStandardOutput.connect(self._read_process_output)
            proc.finished.connect(self._on_process_finished)
            proc.errorOccurred.connect(self._on_process_error)
            proc.start(args[0], args[1:])
            self._process = proc

        def _read_process_output(self) -> None:
            if not self._process:
                return
            data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if data:
                self._append_log(data)

        def _on_process_finished(self, exit_code: int, _status) -> None:
            self._append_log(f"\n--- Terminé (code {exit_code}) ---\n")
            if exit_code != 0:
                QMessageBox.warning(
                    self,
                    "Session interrompue",
                    f"Le processus s'est terminé avec le code {exit_code}.\n"
                    "Consultez le journal ci-dessous (souvent Qt → pygame ou environnement).",
                )
            self._process = None
            self._set_running(False)

        def _on_process_error(self, error) -> None:
            if error == QProcess.ProcessError.FailedToStart:
                self._append_log("\nÉchec du démarrage du processus.\n")
                self._process = None
                self._set_running(False)

        def _stop(self) -> None:
            if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
                self._append_log("\n--- Arrêt demandé ---\n")
                self._process.kill()

        def closeEvent(self, event) -> None:
            if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
                reply = QMessageBox.question(
                    self,
                    "Session en cours",
                    "Une session est en cours. L'arrêter ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
                self._process.kill()
            event.accept()

    app = QApplication(sys.argv)
    win = LauncherWindow()
    win.show()
    return app.exec()
