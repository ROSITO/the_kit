# Démo multi-moteur (Phase 1)

Protocole : Qt → Python → PsychoPy → Pygame (sans médias A/V externes).

```bash
cd ~/Documents/TheKit/the_kit
uv sync --extra qt --extra pygame --extra psychopy --extra lowlatency
uv run python -m the_kit validate -p examples/demo_multi_engine/protocol.json
uv run python -m the_kit check-engines
uv run python -m the_kit check-audio
uv run python -m the_kit run -p examples/demo_multi_engine/protocol.json -s DEMO
```

## av_sync (optionnel)

Copier une paire vidéo+WAV (ex. P1-P9) dans `assets/` et ajouter un nœud :

```json
{
  "id": "loom",
  "type": "av_sync",
  "engine": "psychopy",
  "timing_mode": "low_latency",
  "params": {
    "video": "assets/forward.mp4",
    "audio": "assets/loom.wav",
    "stimulus_duration_s": 2.0
  }
}
```
