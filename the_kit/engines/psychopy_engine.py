from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from the_kit.audio.low_latency import (
    LowLatencyPlayer,
    audio_config_from_protocol,
    choose_device_os_aware,
    plan_av_onsets,
    preload_audio,
    resolve_output_stream_samplerate,
)
from the_kit.engines.base import EngineBase

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node, Protocol


class PsychoPyEngine(EngineBase):
    name = "psychopy"
    _win = None
    _player: LowLatencyPlayer | None = None

    @classmethod
    def check_available(cls) -> tuple[bool, str]:
        try:
            from psychopy import visual  # noqa: F401

            return True, "ok"
        except ImportError:
            return False, "psychopy non installé (uv sync --extra psychopy)"

    def run(
        self,
        protocol: Protocol,
        session: SessionLogger,
        nodes: list[Node],
        *,
        dry_run: bool = False,
    ) -> None:
        from psychopy import core, visual

        display = protocol.raw.get("display") or {}
        if PsychoPyEngine._win is None:
            PsychoPyEngine._win = visual.Window(
                fullscr=bool(display.get("fullscreen", False)),
                screen=int(display.get("screen_index", 0)),
                units="norm",
                color=[-1, -1, -1],
                waitBlanking=True,
                allowGUI=False,
            )
        win = PsychoPyEngine._win

        for node in nodes:
            session.log_event(
                "node_start",
                node_id=node.node_id,
                node_type=node.type,
                node_index=node.index,
                engine=node.engine,
                timing_mode=node.timing_mode,
            )
            try:
                if node.type in ("fixation", "shapes"):
                    self._run_fixation_shapes(win, node, session)
                elif node.type == "av_sync":
                    self._run_av_sync(win, node, protocol, session)
                elif node.type == "audio":
                    self._run_audio_only(node, protocol, session)
                elif node.type == "blank":
                    self._run_blank(win, node, session)
                elif node.type == "photosonde_square":
                    self._run_photosonde(win, node, session)
                elif node.type == "occultation_ttc":
                    self._run_occultation_ttc(win, node, protocol, session)
                elif node.type == "psychopy_stim":
                    self._run_psychopy_stim(win, node, session)
                else:
                    session.log_event(
                        "error",
                        node_id=node.node_id,
                        payload={"message": f"type psychopy inconnu: {node.type}"},
                    )
            finally:
                session.log_event(
                    "node_end",
                    node_id=node.node_id,
                    node_type=node.type,
                    node_index=node.index,
                    engine=node.engine,
                )

    def _run_psychopy_stim(self, win, node: Node, session: SessionLogger) -> None:
        from psychopy import visual

        duration_s = float(node.params.get("duration_s", 1.0))
        stim_type = node.params.get("stim", "text")
        if stim_type == "grating":
            stim = visual.GratingStim(win, tex="sin", mask="gauss", size=0.5)
        else:
            stim = visual.TextStim(
                win, text=node.params.get("text", "+"), height=0.08
            )
        end = time.perf_counter() + duration_s
        while time.perf_counter() < end:
            stim.draw()
            win.flip()

    def _run_occultation_ttc(
        self, win, node: Node, protocol: Protocol, session: SessionLogger
    ) -> None:
        import subprocess
        import sys

        script_rel = node.params.get("script", "occ_action_psychopy.py")
        script_path = (protocol.root / script_rel).resolve()
        if script_path.exists():
            session.log_event(
                "occultation_ttc_subprocess",
                node_id=node.node_id,
                payload={"script": str(script_path)},
            )
            subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(protocol.root),
                check=False,
            )
            return
        from psychopy import visual

        msg = visual.TextStim(
            win,
            text=node.params.get(
                "text",
                "occultation_ttc : placer occ_action_psychopy.py dans le dossier protocole",
            ),
            height=0.05,
            wrapWidth=1.6,
        )
        end = time.perf_counter() + float(node.params.get("duration_s", 3))
        while time.perf_counter() < end:
            msg.draw()
            win.flip()

    def _run_fixation_shapes(self, win, node: Node, session: SessionLogger) -> None:
        from psychopy import core, visual

        duration_s = float(node.params.get("duration_s", 1.0))
        text = node.params.get("text", "+")
        stim = visual.TextStim(
            win, text=text, color=[1, 1, 1], height=0.08, autoLog=False
        )
        end = time.perf_counter() + duration_s
        while time.perf_counter() < end:
            stim.draw()
            win.flip()
            core.wait(0.001)

    def _run_blank(self, win, node: Node, session: SessionLogger) -> None:
        from psychopy import core

        duration_s = float(node.params.get("duration_s", 0.3))
        win.flip()
        core.wait(duration_s)

    def _run_photosonde(self, win, node: Node, session: SessionLogger) -> None:
        import numpy as np
        from psychopy import core, visual

        duration_s = float(node.params.get("duration_s", 0.05))
        size_norm = float(node.params.get("size_norm", 0.12))
        white_tex = np.ones((8, 8, 3), dtype=np.float32)
        flash = visual.ImageStim(
            win,
            image=white_tex,
            units="norm",
            size=(size_norm, size_norm),
            pos=(
                float(node.params.get("pos_x", -0.85)),
                float(node.params.get("pos_y", 0.85)),
            ),
            interpolate=False,
            autoLog=False,
        )
        t0 = time.perf_counter()
        flash.draw()
        flip_perf = win.flip()
        core.wait(duration_s)
        offset_ms = node.params.get("offset_ms")
        session.log_event(
            "photosonde_flash",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            payload={
                "flash_perf": flip_perf,
                "t0_perf": t0,
                "configured_offset_ms": offset_ms,
                "duration_s": duration_s,
            },
        )

    def _ensure_player(self, protocol: Protocol, node: Node) -> tuple[LowLatencyPlayer, str, int | None]:
        audio_cfg = audio_config_from_protocol(protocol.raw, node)
        device_idx, hostapi = choose_device_os_aware(audio_cfg)
        if PsychoPyEngine._player is None:
            PsychoPyEngine._player = LowLatencyPlayer(
                blocksize=int(audio_cfg.get("blocksize", 128)),
                device_index=device_idx,
            )
        stream_sr = resolve_output_stream_samplerate(device_idx, audio_cfg)
        return PsychoPyEngine._player, hostapi, stream_sr

    def _run_audio_only(
        self, node: Node, protocol: Protocol, session: SessionLogger
    ) -> None:
        player, hostapi, stream_sr = self._ensure_player(protocol, node)
        audio_cfg = audio_config_from_protocol(protocol.raw, node)
        rel = node.params.get("file") or node.params.get("audio")
        if not rel:
            raise ValueError("audio node: fichier manquant")
        path = (protocol.root / rel).resolve()
        wave, sr = preload_audio(path, stream_sr)
        _, trial_start, audio_target = plan_av_onsets(
            float(audio_cfg.get("offset_ms", 0)),
            float(audio_cfg.get("scheduling_lead_s", 0.3)),
        )
        player.schedule_wave(wave, sr, audio_target)
        while time.perf_counter() < trial_start:
            pass
        duration_s = float(node.params.get("duration_s", len(wave) / sr + 0.5))
        time.sleep(max(0, duration_s - float(audio_cfg.get("scheduling_lead_s", 0.3))))
        session.log_event(
            "audio_actual_start",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            timing_mode=node.timing_mode,
            payload={
                "audio_actual_start_perf": player.audio_actual_start_perf,
                "audio_hostapi": hostapi,
            },
        )

    def _run_av_sync(
        self, win, node: Node, protocol: Protocol, session: SessionLogger
    ) -> None:
        from psychopy import core, visual

        params = node.params
        video_rel = params.get("video") or params.get("file")
        audio_rel = params.get("audio")
        if not video_rel or not audio_rel:
            raise ValueError("av_sync: params.video et params.audio requis")

        video_path = (protocol.root / video_rel).resolve()
        audio_path = (protocol.root / audio_rel).resolve()
        duration_s = float(params.get("stimulus_duration_s", params.get("duration_s", 2.0)))
        fps = float(params.get("fps", 30.0))

        player, hostapi, stream_sr = self._ensure_player(protocol, node)
        audio_cfg = audio_config_from_protocol(protocol.raw, node)
        wave, sr = preload_audio(audio_path, stream_sr)
        n_samples = min(len(wave), int(duration_s * sr))
        wave = wave[:n_samples]

        offset_ms = float(audio_cfg.get("offset_ms", params.get("offset_ms", 0)))
        lead = float(audio_cfg.get("scheduling_lead_s", 0.3))
        _, trial_start, audio_target = plan_av_onsets(offset_ms, lead)

        frames = self._load_video_frames(win, video_path, fps, duration_s)
        player.schedule_wave(wave, sr, audio_target)

        while time.perf_counter() < trial_start:
            pass

        video_first_flip_perf = None
        t0 = trial_start
        frame_dur = 1.0 / fps
        for i, stim in enumerate(frames):
            target = t0 + i * frame_dur
            while time.perf_counter() < target:
                pass
            stim.draw()
            win.flip()
            if video_first_flip_perf is None:
                video_first_flip_perf = time.perf_counter()

        payload = {
            "audio_target_start_perf": audio_target,
            "audio_actual_start_perf": player.audio_actual_start_perf,
            "video_first_flip_perf": video_first_flip_perf,
            "audio_hostapi": hostapi,
        }
        if player.audio_actual_start_perf and video_first_flip_perf:
            payload["av_offset_measured_ms"] = (
                video_first_flip_perf - player.audio_actual_start_perf
            ) * 1000.0
        session.log_event(
            "video_first_flip",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            timing_mode=node.timing_mode,
            payload=payload,
        )
        self._write_sync_trial(session, node, payload)

    def _load_video_frames(self, win, video_path: Path, fps: float, duration_s: float) -> list:
        from psychopy import visual
        import numpy as np

        try:
            from moviepy.editor import VideoFileClip
        except ImportError:
            from moviepy import VideoFileClip

        clip = VideoFileClip(str(video_path))
        max_frames = int(np.ceil(duration_s * fps))
        stims = []
        for i, frame in enumerate(clip.iter_frames(fps=fps, dtype="uint8")):
            if i >= max_frames:
                break
            norm = (frame.astype(np.float32) / 127.5) - 1.0
            stims.append(
                visual.ImageStim(
                    win,
                    image=norm,
                    size=win.size,
                    units="pix",
                    interpolate=False,
                    autoLog=False,
                )
            )
        clip.close()
        if not stims:
            raise RuntimeError(f"Vidéo sans frames: {video_path}")
        return stims

    def _log_audio_sync(
        self,
        session: SessionLogger,
        node: Node,
        player: LowLatencyPlayer,
        hostapi: str,
        *,
        device_idx: int | None,
        extra: dict,
    ) -> None:
        payload = {
            "audio_actual_start_perf": player.audio_actual_start_perf,
            "audio_hostapi": hostapi,
            **extra,
        }
        session.log_event(
            "audio_actual_start",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            timing_mode=node.timing_mode,
            payload=payload,
        )

    def _write_sync_trial(self, session: SessionLogger, node: Node, payload: dict) -> None:
        path = session.session_dir / "sync_trials.json"
        rows: list[dict[str, Any]] = []
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
        rows.append({"node_id": node.node_id, **payload})
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def cleanup(self) -> None:
        if PsychoPyEngine._player is not None:
            PsychoPyEngine._player.stop()
            PsychoPyEngine._player = None
        if PsychoPyEngine._win is not None:
            try:
                PsychoPyEngine._win.close()
            except Exception:
                pass
            PsychoPyEngine._win = None
