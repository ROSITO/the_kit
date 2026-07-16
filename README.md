# the_kit

Kit d’expérimentation en neurosciences — orchestrateur avec **Qt**, **Pygame**, **PsychoPy**, **tâches Python inline** (fichiers `scripts/*.py`, type OpenSesame) et **audio low-latency** (WASAPI / Core Audio / ALSA…) calqué sur **P1-P9**.

Le projet **Arôme** (`~/Documents/Projet_Arome_ANAELLE`) est l’**exemple de départ** le plus complet (moteur Qt + JSON) ; The Kit unifie Arôme et les autres outils labo sous un même protocole.

**Version actuelle** : `0.5.0a0` — **Phase 4** (export BIDS-like, rapport HTML, Latin square, CI GitHub Actions).

## Démarrage rapide ([uv](https://docs.astral.sh/uv/))

```bash
cd ~/Documents/TheKit/the_kit
uv sync --extra qt --extra pygame --extra lowlatency
# PsychoPy (av_sync) : uv pip install 'psychopy==2023.2.3' moviepy
uv run python -m the_kit check-engines
uv run python -m the_kit validate -p examples/arome_import/minimal_protocol.json
uv run python -m the_kit run -p examples/arome_import/minimal_protocol.json -s TEST --dry-run
```

Sans `uv run`, après activation : `source .venv/bin/activate` puis les mêmes commandes `python -m the_kit …`.

Guide complet : [doc_user.md](./doc_user.md)

## Documentation

| Document | Rôle |
|----------|------|
| [doc_user.md](./doc_user.md) | Installation, CLI, sessions, protocoles Arôme |
| [PRD.md](./PRD.md) | Spécification produit (v1.5) |
| [ROADMAP.md](./ROADMAP.md) | Phases, jalons, critères d’acceptation |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Modules, flux, structure packages |
| [MEMORY.md](./MEMORY.md) | Reprise de contexte / mémoire projet |
| [CLAUDE.md](./CLAUDE.md) | Guide assistants IA |

## Références labo

- **Qt (v0 porté)** : `~/Documents/Projet_Arome_ANAELLE`
- **Pygame** : randomflow, shadowi, MOT, occultation
- **PsychoPy + low-latency** : audi_visuel, P1-P9

## CLI

```bash
uv run python -m the_kit run -p <protocol.json> -s <subject_id> [--dry-run] [--check-media]
uv run python -m the_kit validate -p <protocol.json>
uv run python -m the_kit check-engines
uv run python -m the_kit check-audio
uv run python -m the_kit check-lsl    # uv pip install pylsl
```

| Commande | Rôle |
|----------|------|
| `the_kit design` | Concepteur Qt (presets, validation) |
| `the_kit import-p19 -c config.json -o protocol.json` | Import P1-P9 |
| `the_kit export-zip -p protocol.json -o pack.zip` | Export protocole + assets |
| `the_kit export-session -d sessions/...` | BIDS-like + `session_report.html` |
| `the_kit run ... --export-session` | Idem à la fin du run |

Démos : `examples/demo_multi_engine/`, `examples/demo_phase3/`. Presets : `examples/presets/` (dont `occultation_classic.json`, `shadow_ball_congruent.json`). Calibration terrain : [doc_calibration.md](./doc_calibration.md).
