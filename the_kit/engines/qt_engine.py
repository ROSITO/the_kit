from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from the_kit.engines.base import EngineBase
from the_kit.io.serial_trigger import send_serial_trigger

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node, Protocol


class QtEngine(EngineBase):
    name = "qt"

    @classmethod
    def check_available(cls) -> tuple[bool, str]:
        try:
            import PyQt6  # noqa: F401

            return True, "ok"
        except ImportError:
            return False, "PyQt6 non installé (uv sync --extra qt)"

    _app = None
    _window = None

    def run(
        self,
        protocol: Protocol,
        session: SessionLogger,
        nodes: list[Node],
        *,
        dry_run: bool = False,
    ) -> None:
        from PyQt6.QtCore import Qt, QTimer, QUrl
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PyQt6.QtMultimediaWidgets import QVideoWidget
        from PyQt6.QtWidgets import (
            QApplication,
            QButtonGroup,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QRadioButton,
            QSlider,
            QVBoxLayout,
            QWidget,
        )

        class QuestionnaireWidget(QWidget):
            def __init__(self, node: Node, questions: dict, parent=None):
                super().__init__(parent)
                self.node = node
                self.main_window = parent
                self.layout = QVBoxLayout()
                self.setLayout(self.layout)
                self.widgets: dict = {}
                self._started_perf = __import__("time").perf_counter()

                for question, echelle in questions.items():
                    group_box = QGroupBox(question)
                    group_layout = QVBoxLayout()
                    group_box.setLayout(group_layout)
                    slider_layout = QHBoxLayout()
                    slider_layout.setSpacing(20)
                    slider = QSlider(Qt.Orientation.Horizontal)
                    slider.setMinimum(0)
                    slider.setMaximum(len(echelle) - 1)
                    slider.setTickPosition(QSlider.TickPosition.TicksBelow)
                    slider.setTickInterval(1)
                    slider_layout.addWidget(slider)
                    radio_unknown = QRadioButton("Je ne sais pas")
                    radio_unknown.setStyleSheet(
                        "QRadioButton { margin-right: 20px; color: #666666; }"
                    )
                    slider_layout.addWidget(radio_unknown)
                    slider_layout.addStretch()
                    group_layout.addLayout(slider_layout)
                    self.layout.addWidget(group_box)
                    self.widgets[question] = (slider, radio_unknown, echelle)
                self.layout.addStretch()
                QTimer.singleShot(60000, self.auto_next)

            def auto_next(self) -> None:
                self.main_window.handle_questionnaire(self, self.get_responses())

            def get_responses(self) -> dict[str, str]:
                responses = {}
                for question, (slider, radio, echelle) in self.widgets.items():
                    if radio.isChecked():
                        responses[question] = "Je ne sais pas"
                    else:
                        idx = slider.value()
                        responses[question] = echelle[idx] if 0 <= idx < len(echelle) else ""
                return responses

        class WaitKeyWidget(QWidget):
            def __init__(self, node: Node, parent=None):
                super().__init__(parent)
                self.node = node
                self.main_window = parent
                key_char = node.params.get("key", "t")
                self.key_char = str(key_char).lower()
                self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                layout = QVBoxLayout(self)
                message = node.params.get("message") or f"Appuyez sur '{key_char}' pour continuer"
                label = QLabel(message)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 18px; color: #333;")
                layout.addWidget(label)
                self.setFocus()

            def keyPressEvent(self, event: QKeyEvent) -> None:
                if event.text().lower() == self.key_char:
                    self.main_window.handle_wait_key_pressed(self)
                else:
                    super().keyPressEvent(event)

        class MainWindow(QMainWindow):
            def __init__(self) -> None:
                super().__init__()
                self.protocol = protocol
                self.session = session
                self.nodes = nodes
                self.dry_run = dry_run
                self.setWindowTitle(f"The Kit — {protocol.name}")
                self.setGeometry(100, 100, 800, 600)
                self.central_widget = QWidget()
                self.setCentralWidget(self.central_widget)
                self.layout = QVBoxLayout()
                self.central_widget.setLayout(self.layout)
                self.media_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)
                self.video_widget = QVideoWidget()
                self.layout.addWidget(self.video_widget)
                self.media_player.setVideoOutput(self.video_widget)
                self.media_player.errorOccurred.connect(self.handle_error)
                self.media_player.mediaStatusChanged.connect(self.handle_media_status)
                self.current_index = 0
                self.loop_count = 0
                self.max_loops = 1
                self.current_video_label = ""
                self.questionnaire_counter = 0
                self._active_node: Node | None = None
                session.log_event(
                    "session_start",
                    payload={"protocol": protocol.name, "dry_run": dry_run},
                )
                self.show_next_node()

            def handle_error(self, _error, error_string: str) -> None:
                node = self._active_node
                self.session.log_event(
                    "error",
                    node_id=node.node_id if node else None,
                    node_type=node.type if node else None,
                    node_index=node.index if node else None,
                    engine="qt",
                    payload={"message": error_string},
                )
                QMessageBox.critical(self, "Erreur", f"Erreur de lecture vidéo: {error_string}")
                self.advance_node()

            def handle_media_status(self, status) -> None:
                from PyQt6.QtMultimedia import QMediaPlayer

                if status == QMediaPlayer.MediaStatus.LoadedMedia:
                    self.media_player.play()
                    node = self._active_node
                    if node:
                        self.session.log_event(
                            "video_start",
                            node_id=node.node_id,
                            node_type=node.type,
                            node_index=node.index,
                            engine="qt",
                        )

            def show_next_node(self) -> None:
                if self.current_index >= len(self.nodes):
                    self.close()
                    return
                node = self.nodes[self.current_index]
                self.current_index += 1
                self._active_node = node
                self.session.log_event(
                    "node_start",
                    node_id=node.node_id,
                    node_type=node.type,
                    node_index=node.index,
                    engine=node.engine,
                    timing_mode=node.timing_mode,
                )
                if node.type == "video":
                    self.show_video(node)
                elif node.type == "questionnaire":
                    self.show_questionnaire(node)
                elif node.type == "trigger":
                    self.do_trigger(node)
                elif node.type == "wait_key":
                    self.show_wait_key(node)
                elif node.type == "delay":
                    self.do_delay(node)
                elif node.type == "instructions":
                    self.show_instructions(node)
                elif node.type in ("consent", "debrief"):
                    self.show_markdown_screen(node)
                elif node.type == "block_break":
                    self.show_block_break(node)
                elif node.type == "slideshow":
                    self.show_slideshow(node)
                else:
                    self.session.log_event(
                        "error",
                        node_id=node.node_id,
                        payload={"message": f"type inconnu: {node.type}"},
                    )
                    self.show_next_node()

            def advance_node(self, node: Node | None = None) -> None:
                node = node or self._active_node
                if node:
                    self.session.log_event(
                        "node_end",
                        node_id=node.node_id,
                        node_type=node.type,
                        node_index=node.index,
                        engine=node.engine,
                    )
                self._active_node = None
                self.show_next_node()

            def do_trigger(self, node: Node) -> None:
                port = node.params.get("port", "COM4")
                value = int(node.params.get("value", 1))
                try:
                    send_serial_trigger(port, value, dry_run=self.dry_run)
                    self.session.log_event(
                        "trigger",
                        node_id=node.node_id,
                        node_type=node.type,
                        node_index=node.index,
                        engine=node.engine,
                        payload={"port": port, "value": value, "dry_run": self.dry_run},
                    )
                except Exception as exc:
                    self.session.log_event(
                        "error",
                        node_id=node.node_id,
                        node_type=node.type,
                        node_index=node.index,
                        payload={"message": str(exc)},
                    )
                    if not self.dry_run:
                        QMessageBox.warning(
                            self,
                            "Trigger",
                            f"Échec trigger ({port}): {exc}\nPassage au nœud suivant.",
                        )
                self.advance_node(node)

            def _load_text(self, node: Node) -> str:
                params = node.params
                if params.get("file"):
                    p = (self.protocol.root / params["file"]).resolve()
                    return p.read_text(encoding="utf-8") if p.exists() else ""
                return params.get("text", "")

            def show_instructions(self, node: Node) -> None:
                self.show_markdown_screen(node, auto_timer=True)

            def show_markdown_screen(self, node: Node, *, auto_timer: bool = False) -> None:
                self.video_widget.hide()
                text = self._load_text(node)
                label = QLabel(text)
                label.setWordWrap(True)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 16px; padding: 24px; color: #222;")
                self.layout.addWidget(label)
                key = str(node.params.get("key", "space")).lower()
                if auto_timer:
                    QTimer.singleShot(
                        int(float(node.params.get("duration_s", 30)) * 1000),
                        lambda: self._clear_overlay(label, node),
                    )
                else:
                    self._consent_label = label
                    self._consent_node = node
                    self._consent_key = key

            def keyPressEvent(self, event: QKeyEvent) -> None:
                if hasattr(self, "_consent_node") and self._consent_node:
                    want = getattr(self, "_consent_key", "space")
                    pressed = event.text().lower() or (
                        "space" if event.key() == Qt.Key.Key_Space else ""
                    )
                    if want == "space" and event.key() == Qt.Key.Key_Space:
                        label = self._consent_label
                        node = self._consent_node
                        self._consent_node = None
                        self._clear_overlay(label, node)
                        return
                    if pressed and pressed == want:
                        label = self._consent_label
                        node = self._consent_node
                        self._consent_node = None
                        self._clear_overlay(label, node)
                        return
                super().keyPressEvent(event)

            def _clear_overlay(self, label: QLabel, node: Node) -> None:
                label.deleteLater()
                self.video_widget.show()
                self.advance_node(node)

            def show_block_break(self, node: Node) -> None:
                self.video_widget.hide()
                msg = node.params.get("message", "Pause")
                label = QLabel(msg)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 20px;")
                self.layout.addWidget(label)
                QTimer.singleShot(
                    int(float(node.params.get("duration_s", 60)) * 1000),
                    lambda: self._clear_overlay(label, node),
                )

            def show_slideshow(self, node: Node) -> None:
                from PyQt6.QtGui import QPixmap

                images = node.params.get("images") or node.params.get("files") or []
                if not images:
                    self.advance_node(node)
                    return
                self.video_widget.hide()
                label = QLabel()
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.layout.addWidget(label)
                idx = [0]
                interval_ms = int(float(node.params.get("interval_s", 2)) * 1000)

                def show_frame() -> None:
                    if idx[0] >= len(images):
                        self._clear_overlay(label, node)
                        return
                    rel = images[idx[0]]
                    p = (self.protocol.root / rel).resolve()
                    if p.exists():
                        label.setPixmap(
                            QPixmap(str(p)).scaled(
                                label.size(),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                    idx[0] += 1
                    QTimer.singleShot(interval_ms, show_frame)

                show_frame()

            def show_wait_key(self, node: Node) -> None:
                self.video_widget.hide()
                wait_widget = WaitKeyWidget(node, self)
                self.layout.addWidget(wait_widget)

            def handle_wait_key_pressed(self, wait_widget: WaitKeyWidget) -> None:
                node = wait_widget.node
                self.session.log_event(
                    "wait_key",
                    node_id=node.node_id,
                    node_type=node.type,
                    node_index=node.index,
                    engine=node.engine,
                    payload={"key": wait_widget.key_char},
                )
                wait_widget.deleteLater()
                self.video_widget.show()
                self.advance_node(node)

            def show_video(self, node: Node) -> None:
                self.video_widget.show()
                rel = node.params.get("file") or node.raw.get("file")
                video_path = (self.protocol.root / rel).resolve()
                if not video_path.exists():
                    QMessageBox.critical(
                        self, "Erreur", f"Fichier vidéo introuvable: {video_path}"
                    )
                    self.advance_node(node)
                    return
                self.current_video_label = os.path.basename(str(video_path))
                self.media_player.setSource(QUrl.fromLocalFile(str(video_path)))
                self.audio_output.setVolume(1.0)
                duration_s = float(
                    node.params.get("duration_s") or node.raw.get("time") or 1
                )
                QTimer.singleShot(int(duration_s * 1000), lambda: self.advance_node(node))

            def show_questionnaire(self, node: Node) -> None:
                self.video_widget.hide()
                questions = {}
                params = {**node.raw, **node.params}
                echelle = params.get("echelle", [])
                for i in range(20):
                    key = f"question{i + 1}"
                    if key in params:
                        questions[params[key]] = echelle
                questionnaire = QuestionnaireWidget(node, questions, self)
                self.layout.addWidget(questionnaire)

            def handle_questionnaire(self, widget: QuestionnaireWidget, responses: dict) -> None:
                node = widget.node
                self.questionnaire_counter += 1
                stimulus = self.current_video_label or node.node_id
                for question, answer in responses.items():
                    self.session.log_response(
                        node_index=node.index,
                        node_type=node.type,
                        node_id=node.node_id,
                        stimulus=stimulus,
                        response=f"{question}: {answer}",
                        engine=node.engine,
                    )
                widget.deleteLater()
                self.advance_node(node)

            def do_delay(self, node: Node) -> None:
                duration_s = float(node.params.get("duration_s", 1))
                QTimer.singleShot(int(duration_s * 1000), lambda: self.advance_node(node))

            def closeEvent(self, event) -> None:
                super().closeEvent(event)

        app = QApplication.instance() or QApplication(sys.argv)
        QtEngine._app = app
        window = MainWindow()
        QtEngine._window = window
        window.show()
        app.exec()

    def cleanup(self) -> None:
        if QtEngine._window is not None:
            try:
                QtEngine._window.close()
            except Exception:
                pass
            QtEngine._window = None
        if QtEngine._app is not None:
            try:
                QtEngine._app.quit()
                QtEngine._app.processEvents()
            except Exception:
                pass
            QtEngine._app = None
