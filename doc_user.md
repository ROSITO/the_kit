# Guide utilisateur — The Kit (Phase 0)

## Prérequis

- [uv](https://docs.astral.sh/uv/) installé (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Installation

```bash
cd ~/Documents/TheKit/the_kit
uv sync --extra qt --extra pygame --extra lowlatency
uv pip install 'psychopy==2023.2.3' moviepy   # optionnel — av_sync
```

`uv` crée un environnement dans `.venv/` (géré automatiquement, pas besoin de `python -m venv`).

| Commande | Effet |
|----------|--------|
| `uv sync --extra qt` | Phase 0 : The Kit + PyQt6 + pyserial + outils dev (pytest, jsonschema) |
| `uv sync --extra qt --extra dev` | Identique si le groupe `dev` n’est pas déjà par défaut |
| `uv sync --all-extras` | Tous les profils déclarés dans `pyproject.toml` (futur : pygame, psychopy…) |

Les fichiers `requirements-*.txt` restent une **référence** ; la source de vérité est `pyproject.toml` + `uv.lock`.

## Vérifier l’environnement

```bash
uv run python -m the_kit check-engines
uv run python -m the_kit validate -p examples/arome_import/minimal_protocol.json
```

## Lancer une session

```bash
uv run python -m the_kit run \
  -p examples/arome_import/minimal_protocol.json \
  -s S001 \
  --dry-run
```

### Lanceur graphique (technicien)

```bash
uv run python -m the_kit launch
```

Fenêtre Qt : choix du `protocol.json`, ID participant, options (dry-run, vérifier médias), bouton **Lancer**.  
Sur macOS : double-clic `scripts/launch_the_kit.command`.

| Option | Description |
|--------|-------------|
| `-p` / `--protocol` | Fichier JSON (v1 ou Arôme v0, migré automatiquement) |
| `-s` / `--subject` | Identifiant participant |
| `--session-dir` | Dossier de sortie (défaut : `sessions/YYYYMMDD_HHMMSS_<subject>`) |
| `--dry-run` | Triggers série simulés (pas d’écriture COM) |
| `--check-media` | Refuse le run si les vidéos/images sont absentes |

## Sorties session

Dans le dossier session :

| Fichier | Contenu |
|---------|---------|
| `events.jsonl` | Journal horodaté (démarrage/fin nœuds, réponses, triggers) |
| `responses.csv` | Réponses questionnaire (colonnes normalisées) |
| `protocol_executed.json` | Copie du protocole exécuté |
| `session_meta.json` | Version The Kit, hash protocole, sujet |

## Protocoles Arôme existants

Les fichiers `experiment*.json` du projet Arôme sont chargés tels quels (migration v0 → v1). Exécuter depuis le répertoire contenant `video/` :

```bash
cd ~/Documents/Projet_Arome_ANAELLE/Projet_Arome_ANAELLE
uv run --project ~/Documents/TheKit/the_kit python -m the_kit run \
  -p experiment9_notrig.json -s S001 --dry-run
```

(`--project` pointe vers le dépôt The Kit ; les chemins `video/…` du JSON restent relatifs au répertoire courant.)

Voir [examples/arome_import/README.md](./examples/arome_import/README.md).

## Profils multiples (Phase 1+)

Sur un même poste, **pygame** et **psychopy** peuvent entrer en conflit. Modèle recommandé (comme `audi_visuel`) :

```bash
# Environnement dédié pygame (exemple futur)
uv sync --extra pygame --no-default-groups

# Environnement dédié psychopy (exemple futur)
uv sync --extra psychopy --no-default-groups
```

Ou deux répertoires / lockfiles séparés — à documenter en Phase 1.

## Types de nœuds Phase 0

`video`, `questionnaire`, `trigger`, `wait_key`, `delay` — moteur `qt` uniquement.

## Phase 2 — conditions & concepteur

```bash
# Importer un config P1-P9
uv run python -m the_kit import-p19 \
  -c ~/Documents/P1-P9_remastered/P1-P9_remastered/manip_psychophysique_json/config.json \
  -o protocol_p19.json

# Concepteur (Qt)
uv run python -m the_kit design

# Export zip
uv run python -m the_kit export-zip -p protocol.json -o mon_protocole.zip
```

Presets : `examples/presets/video_qcm.json`, `optic_flow_bm.json`, `looming_conditions.json`.

Chaque session écrit aussi `environment.json` (hash médias, versions).

Phase 1 : [doc_technician.md](./doc_technician.md), démo `examples/demo_multi_engine/`.

## Phase 3 — scènes labo, LSL, EyeLink

### Nœuds pygame

| Type | Params clés |
|------|-------------|
| `occultation` | `occultation_time`, `ball_speed`, `circle_option` (0/1/2), `max_duration_s` |
| `shadow_ball` | Corridor 3D (damiers, mur, point de fuite) — port **shadowi**. Modes : `baseline`, `congruent`, `congruent_levit`, `incongruent_black`, `incongruent_white`. Params : `fixation_duration_s` (déf. 3), `ball_traverse_time_s`, `run_baseline_pair` (baseline puis condition, comme shadowi), `room_depth`, `center_crossings` |
| `mot` | `num_balls`, `duration_s`, `keyhole_radius` |

### LSL

Ajouter en tête du protocole :

```json
"lsl": {
  "enabled": true,
  "stream_name": "TheKit_Markers",
  "stream_type": "Markers"
}
```

```bash
uv pip install pylsl
uv run python -m the_kit check-lsl
```

Les événements `node_start`, `audio_actual_start`, etc. sont repoussés sur le stream (codes dans `io/lsl.py`).

### EyeLink

Script exemple : `examples/scripts/eyelink_calib.py` (nœud `python_task`). Nécessite le SDK SR Research (`pylink`) ; `dummy_mode: true` pour tests sans tracker.

### Démo

```bash
uv run python -m the_kit run -p examples/demo_phase3/protocol.json -s DEMO3
```

Presets : `examples/presets/occultation_classic.json`, `shadow_ball_congruent.json`.

Calibration A/V terrain : [doc_calibration.md](./doc_calibration.md).

## Phase 4 — export session & counterbalancing

### Export BIDS-like + rapport HTML

```bash
# Après un run
uv run python -m the_kit export-session -d sessions/20260522_164848_DEMO3

# Ou directement à la fin du run
uv run python -m the_kit run -p protocol.json -s S001 --export-session
```

Génère dans le dossier session :
- `bids/participants.tsv`, `bids/*_events.tsv`, `dataset_description.json`
- `session_report.html` (résumé expérimentateur)

### Latin square

Dans le protocole avec `conditions[]` :

```json
"presentation": {
  "counterbalance": "latin_square",
  "randomize_trials": false
},
"subject": { "number": 2 }
```

Preset : `examples/presets/conditions_latin_square.json`

Lanceur macOS (double-clic) : `scripts/run_the_kit.command`

## Scène composable (`pygame_scene`) — fond + stimuli

Un seul nœud combine un **fond** et un ou plusieurs **stimuli** superposés.

| Fond (`background`) | Stimuli (`stimuli[]`) |
|---------------------|------------------------|
| `plain` / `black` | `mot`, `optic_flow` / `flow`, `shadow_ball` / `ball` |
| `shadow_corridor` / `shadow` | idem (ex. MOT dans le couloir damier) |

Exemple — MOT dans le corridor shadowi :

```bash
uv run python -m the_kit run -p examples/presets/shadow_corridor_mot.json -s MOT1
```

```json
{
  "type": "pygame_scene",
  "engine": "pygame",
  "params": {
    "background": "shadow_corridor",
    "background_params": { "room_depth": 2.2 },
    "duration_s": 15,
    "stimuli": [
      { "type": "mot", "num_balls": 8, "duration_s": 15, "keyhole": true }
    ]
  }
}
```

Les anciens nœuds (`shadow_ball`, `mot`, `optic_flow` seuls) restent valides ; `pygame_scene` est le mode compositionnel.
