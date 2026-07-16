# Calibration A/V et photosonde (prochaine campagne terrain)

Phase 3 fournit les briques logicielles ; la **validation oscilloscope** reste une procédure labo distincte.

## Prérequis

- Poste calibré (WASAPI / Core Audio, pas Bluetooth)
- `uv sync --extra qt --extra pygame --extra lowlatency`
- `uv pip install psychopy==2023.2.3 moviepy` pour `av_sync`
- Optionnel : `uv pip install pylsl` pour LSL

## Checklist technique

```bash
uv run python -m the_kit check-audio
uv run python -m the_kit check-engines
uv run python -m the_kit check-lsl    # si pylsl installé
```

## Essai A/V (forward + WAV)

1. Importer ou créer un protocole avec `conditions[]` (P1-P9) ou nœud `av_sync`
2. Lancer : `uv run python -m the_kit run -p protocol.json -s CALIB --check-media`
3. Mesurer à l’oscillo :
   - `audio_actual_start_perf` vs `video_first_flip_perf` dans `sync_trials.json`
   - Ajuster `audio_defaults.offset_ms` dans le JSON
4. Répéter jusqu’à jitter &lt; 10 ms (objectif PRD)

## Photosonde

1. Ajouter un nœud `photosonde_square` (psychopy) avant/après `av_sync`
2. Flash coin écran → comparer au front vidéo sur l’oscillo
3. Logger `photosonde_flash` dans `events.jsonl`

## LSL

Protocole avec section :

```json
"lsl": { "enabled": true, "stream_name": "TheKit_Markers" }
```

Vérifier dans LabRecorder que les marqueurs `node_start` / `audio_actual_start` arrivent.

## EyeLink

```json
{
  "type": "python_task",
  "engine": "python",
  "params": {
    "script": { "file": "scripts/eyelink_calib.py" },
    "eyelink": { "dummy_mode": true, "participant_code": "S001" }
  }
}
```

Sur poste EyeLink réel : `dummy_mode: false` + SDK SR Research installé.
