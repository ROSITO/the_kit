# CLAUDE.md — Guide pour assistants IA (The Kit)

Ce fichier oriente Claude / Cursor / autres agents qui modifient **ce dépôt**.  
Lire **[MEMORY.md](./MEMORY.md)** pour le contexte rapide, **[ROADMAP.md](./ROADMAP.md)** pour les phases et critères MVP, **[ARCHITECTURE.md](./ARCHITECTURE.md)** pour la structure technique, **[PRD.md](./PRD.md)** pour la spec complète (v1.5).

---

## 1. Qu’est-ce que The Kit ?

**The Kit** est un orchestrateur de manipulations psychophysiques pour le labo (CerCo / ROSITO).  
Ce n’est **pas** un fork du projet **Arôme** : Arôme (`~/Documents/Projet_Arome_ANAELLE`) est seulement la référence Qt + JSON la plus avancée aujourd’hui.

Un protocole **`protocol.json`** enchaîne des **nœuds** ; chaque nœud déclare :

| Champ | Valeurs | Rôle |
|-------|---------|------|
| `type` | `video`, `questionnaire`, `python_task`, `optic_flow`, … | Quoi faire |
| `engine` | `qt`, `pygame`, `psychopy`, `python` | Qui exécute |
| `timing_mode` | `standard`, `low_latency` | Comment jouer l’audio critique (PortAudio / WASAPI) |

**État actuel (2026-05-22)** : **Phase 4 livrée** (`0.5.0a0`) — + export BIDS, rapport HTML, Latin square, CI. **Priorité** : calibration oscillo puis `v1.0.0`.

---

## 2. Documents à lire avant de coder

| Priorité | Fichier | Quand |
|----------|---------|-------|
| 1 | [MEMORY.md](./MEMORY.md) | Reprise de session, chemins labo |
| 2 | [ROADMAP.md](./ROADMAP.md) | Phases 0–3, jalons M0–M4, releases, checklists |
| 3 | [ARCHITECTURE.md](./ARCHITECTURE.md) | Modules, flux, données, engines |
| 4 | [PRD.md](./PRD.md) §4–5 | Moteurs, visuel §4.9, Python §4.10, exigences |
| 5 | [doc_user.md](./doc_user.md) | CLI, installation, sessions |
| 6 | Code externe | Port depuis Arôme / P1-P9 (voir ARCHITECTURE §16) |

### Commandes (Phase 0) — [uv](https://docs.astral.sh/uv/)

```bash
uv sync --extra qt
uv run python -m the_kit check-engines
uv run python -m the_kit validate -p <protocol.json>
uv run python -m the_kit run -p <protocol.json> -s <subject> [--dry-run] [--check-media]
```

Vault Obsidian (inventaire labo) : `~/Documents/obsidian_vault/Travaux/`

---

## 3. Architecture (résumé)

```text
protocol.json + assets/
        ↓
Orchestrateur (the_kit)
        ↓
┌──────┬────────┬──────────┬─────────┐
│  qt  │ pygame │ psychopy │ python  │  ← engines
└──────┴────────┴──────────┴─────────┘
        ↓
Couche low_latency (sounddevice → WASAPI / Core Audio / ALSA)
        ↓
events.jsonl + responses.csv + session/
```

**Contrat moteur** (PRD §4.2) : `prepare(node, ctx)` → `run(node, ctx) → NodeResult` → logging.

**Horloge sync** : `time.perf_counter()` pour audio/vidéo en `low_latency` (porter depuis P1-P9).

---

## 4. Code source à réutiliser (ne pas réécrire from scratch)

| Besoin | Chemin local |
|--------|----------------|
| Qt vidéo, QCM, trigger, JSON Arôme v0 | `~/Documents/Projet_Arome_ANAELLE/psychophysique_app.py` |
| Audio low-latency, WASAPI, `ScheduledAudioPlayer` | `~/Documents/P1-P9_remastered/P1-P9_remastered/manip_psychophysique_json/main.py` |
| Sync A/V | `~/Documents/P1-P9_remastered/audi_visuel/` |
| Flux optique | `~/Documents/noiseFlow/randomflow/optical_flow.py` |
| Ombre / occultation / MOT | `shadowJB/shadowi`, `occultation_Robin/occultation`, `MOT/` |

Adapter et découper — ne pas copier les monolithes tels quels sans orchestrateur.

---

## 5. Structure cible du package (à créer)

```text
the_kit/
├── __init__.py
├── __main__.py           # python -m the_kit
├── cli.py                # run | validate | check-engines | check-audio | dry-run
├── orchestrator.py
├── task_api.py           # TaskContext, NodeResult (scripts inline)
├── protocol/
│   ├── loader.py         # import Arôme v0 → protocol v1
│   └── schema.py
├── engines/
│   ├── base.py
│   ├── qt_engine.py
│   ├── pygame_engine.py
│   ├── psychopy_engine.py
│   └── python_engine.py
├── audio/
│   └── low_latency.py
├── logging/
│   └── session.py
└── designer/             # Phase 1+
```

Racine repo : aussi `schemas/`, `examples/`, `requirements-*.txt`, tests `tests/`.

---

## 6. Priorités d’implémentation

### Phase 0 ✅ (2026-05-22)

- [x] Package `the_kit` `0.1.0a0` (`pyproject.toml`)
- [x] `protocol/loader.py` + `migrate_arome_v0`
- [x] `orchestrator.py` + `engines/qt_engine.py`
- [x] `logging/session.py` — `events.jsonl` + CSV F-702
- [x] CLI : `run`, `validate`, `check-engines`, `--dry-run`
- [x] Tests pytest + `requirements-qt.txt` + `doc_user.md`

### Phase 1 ✅

- [x] `audio/low_latency.py`, `check-audio`
- [x] `pygame_engine`, `psychopy_engine`, `python_engine`
- [x] `demo_multi_engine`, `doc_technician.md`

### Phase 2 ✅

- [x] `conditions[]`, `import-p19`, `export-zip`, `environment.json`
- [x] `designer/` Qt, presets
- [x] consent/debrief/slideshow/photosonde

### Phase 3 ✅ — LSL, EyeLink, scènes labo, shadowi corridor

### Phase 4 ✅

- [x] `session_export.py` — BIDS-like + `session_report.html`
- [x] `protocol/counterbalance.py` — Latin square
- [x] CLI `export-session`, `run --export-session`
- [x] CI `.github/workflows/ci.yml`, `scripts/run_the_kit.command`

Ne pas implémenter sans demande : TR IRM intégré, cloud.

---

## 7. Règles de conception (obligatoires)

1. **Protocole JSON unique** — pas de chemins hardcodés vers un seul `experiment.json` dans le code.
2. **`engine` + `timing_mode` explicites** dans les logs et l’API interne.
3. **Low-latency** = couche `sounddevice`/PortAudio, pas obligation PsychoPy pour l’audio.
4. **`python_task`** = fichiers sous `{protocol}/scripts/` uniquement ; **jamais** `exec()` de strings JSON (PRD PY-018, F-1501).
5. **Offline-first** — pas de dépendance réseau au run participant.
6. **Session append-only** — `events.jsonl` ; ne pas écraser silencieusement les données participant.
7. **Minimal diff** — étendre l’orchestrateur ; éviter refonte globale non demandée.
8. **Français** pour doc utilisateur et messages UI labo ; identifiants code en anglais (snake_case).

---

## 8. Présentation visuelle (PRD §4.9)

Toujours classer un nœud visuel :

| Famille | Exemples `type` |
|---------|-----------------|
| **A — fichier** | `video`, `image`, `slideshow`, `av_sync` |
| **B — généré** | `shapes`, `optic_flow`, `mot`, `shadow_ball`, `occultation` |
| **C — UI** | `fixation`, `instructions`, `questionnaire`, `blank`, `photosonde_square` |

Exigences détaillées : PRD §5.2 (`V-*`).

---

## 9. Tâches Python inline (OpenSesame)

Nœud JSON :

```json
{
  "type": "python_task",
  "engine": "python",
  "script": {
    "file": "scripts/my_task.py",
    "prepare": "prepare",
    "run": "run",
    "args": {}
  }
}
```

Script :

```python
from the_kit.task_api import NodeResult

def prepare(ctx):
    pass

def run(ctx):
    ctx.log.event("my_step", foo=1)
    return NodeResult(status="ok")
```

Spec complète : **PRD §4.10**, exigences **PY-001…PY-020**.

---

## 10. Protocole JSON minimal (v1)

```json
{
  "protocol_version": "1.0",
  "name": "demo",
  "loop": 1,
  "audio_defaults": {
    "timing_mode": "low_latency",
    "blocksize": 128
  },
  "nodes": [
    {
      "id": "v1",
      "type": "video",
      "engine": "qt",
      "timing_mode": "standard",
      "file": "videos/stim.mp4",
      "duration_s": 10
    }
  ]
}
```

Validation cible : `schemas/protocol-v1.schema.json` + `the_kit validate`.

---

## 11. Commandes (cibles)

```bash
cd ~/Documents/TheKit/the_kit

# Quand implémenté :
python -m the_kit run --protocol ./examples/demo/protocol.json --subject S001
python -m the_kit validate ./examples/demo/protocol.json
python -m the_kit check-engines
python -m the_kit check-audio
python -m the_kit dry-run --protocol ./examples/demo/protocol.json

# Test régression Arôme (manuel jusqu’à import auto) :
cd ~/Documents/Projet_Arome_ANAELLE && python psychophysique_app.py
```

Environnements : prévoir **venv séparés** si pygame + psychopy sur le même poste (conflits pip documentés dans PRD F-904).

---

## 12. Tests

- **pytest** pour parse protocole, adaptateur Arôme, `python_task` mock.
- Pas de matériel requis en CI : mocker audio/vidéo.
- Test manuel low-latency : poste Windows + WASAPI + essai forward/WAV (P1-P9).

---

## 13. Ce qu’il ne faut pas faire

- Renommer le produit en « Arôme 2 » ou fusionner tout dans un seul moteur Qt.
- Mettre du code Python inline dans les champs JSON.
- Charger des scripts Python hors `{protocol_root}/scripts/`.
- Ignorer `timing_mode` et tout passer par `QMediaPlayer` pour des essais sync IRM/psycho.
- Ajouter cloud, base de données centrale, ou stats intégrées (hors scope v1).
- Commits ou push sans demande explicite de l’utilisateur.
- Modifier `~/Documents/Projet_Arome_ANAELLE` ou autres dépôts labo sans instruction claire (The Kit les **lit**, ne les remplace pas in situ).

---

## 14. Après chaque livraison significative

1. Mettre à jour **[MEMORY.md](./MEMORY.md)** §2 (état) et §13 (journal).
2. Si changement de scope : ajuster **[PRD.md](./PRD.md)** (version + changelog en bas).
3. Ajouter ou mettre à jour tests et `examples/` correspondant.

---

## 15. Liens rapides

| Ressource | Chemin |
|-----------|--------|
| PRD complet | [PRD.md](./PRD.md) |
| Mémoire projet | [MEMORY.md](./MEMORY.md) |
| Licence | [LICENSE](./LICENSE) |
| Index labo Obsidian | `~/Documents/obsidian_vault/Travaux/00-Index.md` |

---

*Fichier maintenu pour les agents IA — humains : préférer MEMORY.md + PRD.md.*
