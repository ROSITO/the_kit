# Guide technicien — audio low-latency (Phase 1)

## Installation profil labo

```bash
uv sync --extra qt --extra pygame --extra psychopy --extra lowlatency
uv run python -m the_kit check-audio
uv run python -m the_kit check-engines
```

## WASAPI / Core Audio

The Kit utilise **PortAudio** via `sounddevice`. Sous Windows, l’heuristique préfère **WASAPI** ; sous macOS **Core Audio** ; sous Linux ALSA/JACK/Pulse.

```bash
uv run python -m the_kit check-audio
```

Vérifier que `hostapi` affiché correspond au pilote attendu (pas Bluetooth pour sync A/V).

## Paramètres protocole

| Champ | Défaut | Rôle |
|-------|--------|------|
| `audio_defaults.blocksize` | 128 | Taille buffer callback (64 sur poste dédié) |
| `audio_defaults.scheduling_lead_s` | 0.3 | Délai avant `trial_start_perf` |
| `audio_defaults.offset_ms` | 0 | Décalage audio vs vidéo (ms) |
| `timing_mode` | `low_latency` sur `av_sync` | Active `ScheduledAudioPlayer` |

## Logs sync

Fichier session `sync_trials.json` : `audio_actual_start_perf`, `video_first_flip_perf`, `av_offset_measured_ms`, `audio_hostapi`.

## Conflits pygame ↔ psychopy

Sur un même poste, préférer **deux environnements uv** séparés si pip échoue :

```bash
uv sync --extra qt --extra pygame --no-default-groups
# autre répertoire ou venv
uv sync --extra psychopy --extra lowlatency --no-default-groups
```

Référence : modèle `audi_visuel` (2 venv).

## LSL (Phase 3)

```bash
uv pip install pylsl
uv run python -m the_kit check-lsl
```

Section protocole `lsl` : marqueurs automatiques sur `events.jsonl` (codes dans `the_kit/io/lsl.py`). Vérifier dans LabRecorder avant une session NIRS/fNIRS.

## EyeLink (Phase 3)

SDK SR Research requis (`pylink`). Script de calibration : `examples/scripts/eyelink_calib.py` en `python_task` avec `dummy_mode: true` hors salle.

## NI-DAQ — stimulation sortante (Alba / nidaqmx)

```bash
uv sync --extra ni
uv run python -m the_kit check-ni
```

Section protocole (connexion persistante AO0/AO1) :

```json
"ni_daq": {
  "enabled": true,
  "device": "Dev1",
  "channels": ["ao0", "ao1"],
  "rate": 400,
  "simulation_mode": false
}
```

Nœud `ni_stim` (onde carrée, directions `AP`, `PA`, `LATD`, `LATG`) :

```json
{
  "type": "ni_stim",
  "engine": "python",
  "params": {
    "direction": "AP",
    "amplitude": 1.2,
    "frequency": 0.278,
    "duration_s": 3.6
  }
}
```

Preset : `examples/presets/ni_stim_alba_demo.json`. Porté depuis `shadowi/exemple/Alba_Eyelink_NiDAQmxVers.py`.

`--dry-run` sur `the_kit run` force la simulation NI (pas d'écriture carte).

## Protocole GVS + fNIRS

Preset complet : `examples/neuroconn_gvs/protocol.json` — 50 essais, rampe 10 s, manette Switch, marqueurs LSL par condition (101–105). Voir `examples/neuroconn_gvs/README.md`.

## Calibration oscilloscope

Procédure complète : [doc_calibration.md](./doc_calibration.md) (jitter A/V, photosonde, ajustement `offset_ms`).
