# NeuroConn GVS + fNIRS

Protocole galvanique vestibulaire (GVS) pour **NeuroConn**, piloté par carte **NI-DAQ** (±10 V, 400 Hz), avec marqueurs **LSL** pour enregistrement **fNIRS** (LabRecorder).

Ce dossier contient le protocole complet (`protocol.json`), une version courte pour tests (`protocol_dryrun.json`), les consignes audio MP3 et la configuration matérielle.

---

## Sommaire

1. [Matériel requis](#matériel-requis)
2. [Installation — uv (macOS / Linux / dev)](#installation--uv-macos--linux--dev)
3. [Installation — conda (poste labo Windows)](#installation--conda-poste-labo-windows)
4. [Vérifications avant session](#vérifications-avant-session)
5. [Lancer une session](#lancer-une-session)
6. [Déroulement expérimental](#déroulement-expérimental)
7. [Marqueurs LSL](#marqueurs-lsl)
8. [Stimulation NI (rampe)](#stimulation-ni-rampe)
9. [Fichiers audio](#fichiers-audio)
10. [Paramètres du protocole](#paramètres-du-protocole)
11. [Sorties session](#sorties-session)
12. [Dépannage](#dépannage)

---

## Matériel requis

| Composant | Détail |
|-----------|--------|
| **Carte NI** | Ex. `Dev1/ao0`, `Dev1/ao1` — driver **NI-DAQmx** installé |
| **NeuroConn** | Réception ±10 V, calibration courant côté appareil |
| **fNIRS** | LabRecorder (ou équivalent) abonné au stream LSL **`Trigger`** |
| **Écran** | Fixation centrale (pygame plein écran ou fenêtré selon config OS) |
| **Entrées** | Clavier flèches **ou** Joy-Con / Switch |
| **Audio** | Haut-parleurs pour consignes MP3 |

### Manette Joy-Con

The Kit utilise une **chaîne de backends** (pas un mapping bouton artisanal) :

1. **SDL GameController** — API standard (`d-pad` sémantique) — recommandé
2. **pygame joystick** — repli indices boutons
3. **pyjoycon** (optionnel) — accès HID direct Nintendo

Installation driver Joy-Con (si SDL ne suffit pas) :

```bash
uv sync --extra pygame --extra gamepad
# ou conda :
pip install -e ".[pygame,gamepad]"
```

**Diagnostic obligatoire** avant une session :

```bash
python -m the_kit check-gamepad
```

Appuyez sur la croix : le terminal doit afficher `→ AP`, `→ PA`, etc.

Dans `protocol.json` :

```json
"gamepad_backend": "auto"
```

Valeurs : `auto` | `sdl` | `pygame` | `pyjoycon` | `joycon`

---

## Installation — uv (macOS / Linux / dev)

[uv](https://docs.astral.sh/uv/) est la méthode recommandée pour le développement et macOS.

```bash
cd ~/Documents/TheKit/the_kit

# Dépendances principales + Qt + Pygame + NI + audio
uv sync --extra qt --extra pygame --extra ni --extra lowlatency

# LSL (marqueurs fNIRS) — paquet PyPI séparé
uv pip install pylsl

# Vérifier l'environnement
uv run python -m the_kit check-engines
uv run python -m the_kit check-ni
uv run python -m the_kit check-lsl
```

Toutes les commandes ci-dessous utilisent le préfixe `uv run` (ou activez `.venv` : `source .venv/bin/activate`).

---

## Installation — conda (poste labo Windows)

Sur le poste Windows du labo (sans uv), créer un environnement dédié :

```cmd
conda create -n the_kit python=3.12 -y
conda activate the_kit

cd C:\chemin\vers\the_kit

pip install -e ".[qt,pygame,ni,lowlatency]"
pip install pylsl
```

**Audio Windows** : le profil `lowlatency` installe `sounddevice` → **WASAPI** (prioritaire). Les consignes MP3 du protocole GVS passent par PortAudio, pas `pygame.mixer`.

**Prérequis Windows supplémentaires :**

- Driver **NI-DAQmx** (National Instruments) — [ni.com/downloads](https://www.ni.com/en/support/downloads.html)
- PyQt6 et pygame s’installent via pip ; en cas d’erreur PyQt6, essayer `conda install pyqt` puis `pip install PyQt6`

Vérification :

```cmd
python -m the_kit check-engines
python -m the_kit check-ni
python -m the_kit check-lsl
```

---

## Vérifications avant session

| Commande | Attendu |
|----------|---------|
| `check-engines` | `qt: ok`, `pygame: ok`, `python: ok` |
| `check-ni` | `NI-DAQ : …` (simulation OK en test) |
| `check-lsl` | `LSL : …` + marqueur test **99** |
| `validate -p examples/neuroconn_gvs/protocol.json` | `OK — neuroconn_gvs_nirs (2 nœuds)` |

**Poste labo réel** — dans `protocol.json`, vérifier :

```json
"ni_daq": {
  "enabled": true,
  "simulation_mode": false,
  ...
}
```

Avec `"simulation_mode": true` **ou** l’option CLI `--dry-run`, **aucune tension** n’est envoyée sur la carte NI.

Au lancement d’une vraie session, le terminal doit afficher :

```text
NI-DAQ : connecté — Dev1/ao0, Dev1/ao1 @ 400.0 Hz
```

Puis, à chaque essai :

```text
NI write ramp_AP: N=4000 dur=10.00s amp≈1.200V → carte
🎯 LSL Trigger 2 (stim_onset_AP)
```

---

## Lancer une session

### Option A — Lanceur graphique (recommandé technicien)

Interface Qt : choix du protocole, ID participant, options.

```bash
# uv
uv run python -m the_kit launch

# conda
python -m the_kit launch
```

**macOS** : double-clic sur `scripts/launch_the_kit.command` à la racine du dépôt.

Dans le lanceur :

1. **Parcourir…** → sélectionner `examples/neuroconn_gvs/protocol.json` (ou `protocol_dryrun.json` pour test)
2. Saisir l’**ID participant** (ex. `S001`)
3. Cocher **Dry-run** uniquement pour test sans matériel
4. **Lancer** — le journal s’affiche en bas de fenêtre

### Option B — Ligne de commande

**Session participant (50 essais, baseline 60 s) :**

```bash
uv run python -m the_kit run \
  -p examples/neuroconn_gvs/protocol.json \
  -s S001 \
  --check-media
```

**Dry-run rapide (10 essais, baseline 3 s, NI simulé) :**

```bash
uv run python -m the_kit run \
  -p examples/neuroconn_gvs/protocol_dryrun.json \
  -s DRYRUN \
  --dry-run
```

| Option CLI | Effet |
|------------|-------|
| `-p` / `--protocol` | Chemin vers `protocol.json` |
| `-s` / `--subject` | Identifiant participant |
| `--dry-run` | NI + triggers simulés (pas de tension réelle) |
| `--check-media` | Refuse le run si MP3 manquants |
| `--export-session` | Génère BIDS-like + rapport HTML en fin de session |

---

## Déroulement expérimental

### Vue d’ensemble

```text
Consignes Qt (8 s)
    ↓
Son debut_dexpe.mp3
    ↓
Baseline 60 s (fixation)     → trigger 1 début / fin
    ↓
× 50 essais (ordre aléatoire, 10 × 5 conditions)
    ↓
Fin bloc                     → trigger 1
```

### Par essai

| Étape | Durée | Réponse | Trigger LSL |
|-------|-------|---------|-------------|
| Stimulation GVS (rampe) | 10 s | **Interdite** | **2–6** à l’onset (selon condition) |
| Son `vous_pouvez_repondre.mp3` | ~2,2 s | Interdite | — |
| Fenêtre de réponse | 5 s max | Optionnelle (flèches / manette) | — |
| Si réponse → `Votre_reponse.mp3` | ~3,8 s | — | **8** |
| Si pas de réponse → `fin_du_temps.mp3` | ~3,3 s | — | — |
| ITI | 10 + U(1,5) s | — | **7** (après le son de feedback) |

**Comportement réponse :**

- Le décompte des **5 s** commence **après** la fin de `vous_pouvez_repondre.mp3`.
- Dès la **première** réponse : lecture immédiate de `Votre_reponse.mp3` et **fin** de la fenêtre (plus d’attente).
- Le sujet peut **ne pas répondre** : après 5 s, `fin_du_temps.mp3` est joué.
- Le **RT** est mesuré depuis la fin de `vous_pouvez_repondre.mp3` jusqu’à la réponse.

### Conditions (50 essais)

| Condition | Direction perçue attendue | Code LSL (onset stim) |
|-----------|---------------------------|------------------------|
| **AP** | Avant (↑) | **2** |
| **PA** | Arrière (↓) | **3** |
| **LATG** | Gauche (←) | **4** |
| **LATD** | Droite (→) | **5** |
| **CONTROL** | Rampe mélangée (pas de « bonne » réponse) | **6** |

10 répétitions par condition, ordre mélangé (`random_seed` dans le JSON).

---

## Marqueurs LSL

Stream LabRecorder : nom **`Trigger`**, format **int32**, source `the_kit_gvs`.

| Code | Événement |
|------|-----------|
| **1** | Début / fin de bloc GVS ; début / fin baseline |
| **2** | Stim onset — AP |
| **3** | Stim onset — PA |
| **4** | Stim onset — LATG |
| **5** | Stim onset — LATD |
| **6** | Stim onset — CONTROL |
| **7** | Début ITI (après son de feedback) |
| **8** | Réponse enregistrée |

Chaque trigger s’affiche dans le terminal : `🎯 LSL Trigger N (label)`.

`auto_markers: false` dans le protocole — pas de marqueurs parasites `node_start` / `node_end`.

---

## Stimulation NI (rampe)

Forme d’onde **trapèze 10 s** (≠ onde carré Alba) :

| Phase | Durée |
|-------|-------|
| Montée | 3 s |
| Plateau | 4 s |
| Descente | 3 s |

- **Canaux** : `ao0`, `ao1` (matrice 2×N, style Alba)
- **Amplitude** : `1.2` V par défaut (`params.amplitude`) — à calibrer en mA côté NeuroConn
- **Fréquence d’échantillonnage** : 400 Hz
- **ITI** : 10 s + jitter uniforme [1, 5] s

Configuration dans `protocol.json` → section `ni_daq` et nœud `gvs_block` → `params`.

---

## Fichiers audio

Tous les MP3 sont dans **ce dossier** (`examples/neuroconn_gvs/`) :

| Fichier | Rôle | Durée ≈ |
|---------|------|---------|
| `debut_dexpe.mp3` | Annonce début expérience | 2,1 s |
| `vous_pouvez_repondre.mp3` | Ouverture fenêtre réponse | 2,2 s |
| `Votre_reponse.mp3` | Feedback « réponse enregistrée » | 3,8 s |
| `fin_du_temps.mp3` | Feedback « temps écoulé » | 3,3 s |

Chemins surchargeables dans le JSON :

```json
"sounds": {
  "debut_dexpe": "debut_dexpe.mp3",
  "vous_pouvez_repondre": "vous_pouvez_repondre.mp3",
  "votre_reponse": "Votre_reponse.mp3",
  "fin_du_temps": "fin_du_temps.mp3"
}
```

### WASAPI (Windows) / Core Audio (macOS)

Le protocole déclare :

```json
"audio_defaults": {
  "timing_mode": "low_latency",
  "backend": "auto",
  "blocksize": 128
}
```

| `backend` | Comportement |
|-----------|--------------|
| `auto` | PortAudio (WASAPI sous Windows) si `sounddevice` installé, sinon `pygame.mixer` |
| `portaudio` | Force WASAPI / Core Audio |
| `pygame` | Force `pygame.mixer` (repli) |

Au démarrage du bloc GVS, le terminal affiche le backend utilisé :

```text
🔊 WASAPI — debut_dexpe.mp3 (2.12s)
```

Vérifier le périphérique :

```bash
python -m the_kit check-audio
```

Forcer un casque USB (ex.) via le protocole :

```json
"audio_defaults": {
  "backend": "auto",
  "audio_device_query": "usb"
}
```

Ou index PortAudio explicite : `"audio_device_index": 12` (lister avec `python -m sounddevice`).

---

## Paramètres du protocole

Fichiers :

| Fichier | Usage |
|---------|-------|
| `protocol.json` | Session réelle — 50 essais, baseline 60 s |
| `protocol_dryrun.json` | Test — 10 essais (2×5), baseline 3 s, NI simulé |

Paramètres principaux (`gvs_block` → `params`) :

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `amplitude` | `1.2` | Amplitude rampe (V) |
| `repetitions_per_condition` | `10` | Essais par condition |
| `rise_s` / `plateau_s` / `fall_s` | 3 / 4 / 3 | Forme trapèze (s) |
| `baseline_s` | `60.0` | Baseline initiale (s) |
| `response_window_s` | `5.0` | Fenêtre réponse après consigne (s) |
| `iti_base_s` | `10.0` | ITI de base (s) |
| `iti_jitter_s` | `[1.0, 5.0]` | Jitter ITI uniforme (s) |
| `random_seed` | `42` | Graine ordre des essais |

---

## Sorties session

Dossier : `sessions/YYYYMMDD_HHMMSS_<subject>/`

| Fichier | Contenu |
|---------|---------|
| `events.jsonl` | Événements horodatés (baseline, essais, stim, réponses) |
| `responses.csv` | Réponses par essai (`response`, `rt_ms`) |
| `protocol_executed.json` | Copie du protocole exécuté |
| `environment.json` | Versions Python, OS, dépendances |

Export optionnel : `python -m the_kit export-session -d sessions/...`

---

## Dépannage

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| `NI-DAQ : SIMULATION` en session réelle | `--dry-run` ou `simulation_mode: true` | Retirer `--dry-run`, mettre `simulation_mode: false` |
| Pas de triggers LSL | `pylsl` absent ou LabRecorder non abonné | `pip install pylsl` ; vérifier stream `Trigger` |
| Pas de son | MP3 absents ou backend audio | `--check-media` ; `check-audio` ; vérifier `🔊 WASAPI` dans le terminal |
| `Erreur : module 'pygame.event' has no attribute 'PUMP'` | Ancienne version | Mettre à jour le dépôt |
| Essais très courts en dry-run | Normal | NI simulé (~50 ms) ; en labo la stim dure 10 s réelles |
| Carte NI introuvable | Mauvais `device` ou driver | NI MAX → vérifier nom (`Dev1`) ; `check-ni` |

---

## Références

- Guide utilisateur global : [doc_user.md](../../doc_user.md)
- NI-DAQ / technicien : [doc_technician.md](../../doc_technician.md)
- Code handler : `the_kit/pygame_handlers/neuroconn_gvs.py`
- Marqueurs LSL : `the_kit/io/gvs_lsl.py`
