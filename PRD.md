# PRD — The Kit  

| | |
|---|---|
| **Produit** | Plateforme de création et d’exécution de manipulations psychophysiques simplifiées |
| **Moteurs** | **Qt**, **Pygame**, **PsychoPy**, **Python inline** + couche **low-latency** (PortAudio / WASAPI…) |
| **Exemple de départ** | **Arôme** (`~/Documents/Projet_Arome_ANAELLE`) — pas le périmètre final |
| **Docs projet** | [MEMORY.md](./MEMORY.md) · [README.md](./README.md) |
| **Inventaire labo** | vault `obsidian_vault/Travaux/` |
| **Version PRD** | **1.5** — 2026-05-22 |

### Table des matières

1. [Vision et objectifs](#1-vision-et-objectifs)  
2. [Référence Arôme](#2-référence-de-départ--projet-arôme-exemple-pas-le-produit)  
3. [Personas et parcours](#3-personas-et-cas-dusage)  
4. [Architecture](#4-architecture-cible-conceptuelle) — [**§4.9 Visuel**](#49-présentation-visuelle-taxonomie) · [**§4.10 Tâches Python**](#410-tâches-python-inline--opensesame)  
5. [Exigences fonctionnelles](#5-exigences-fonctionnelles) — [**§5.2 Visuel**](#52-présentation-visuelle-stimulus-à-lécran) · [**§5.18 Tâches Python**](#518-tâches-python-fichier--inline)  
6. [Schéma protocole & données](#6-schéma-de-protocole-cible-évolution-json)  
7. [Exigences non fonctionnelles](#7-exigences-non-fonctionnelles)  
8. [Roadmap](#8-roadmap-proposée) — détail : [ROADMAP.md](./ROADMAP.md)  
9. [Mapping Travaux](#9-mapping-inventaire-travaux--fonctionnalités)  
10. [Critères MVP](#10-critères-dacceptation-v1-mvp)  
11. [Risques](#11-risques-et-mitigations)  
12. [Dépôts](#12-fichiers-et-dépôts)  
13. [Matrice matériel](#13-matrice-matériel-et-pilotes)  
14. [Positionnement](#14-positionnement-vs-outils-existants)  
15. [Qualité & releases](#15-qualité-tests-et-versionnement)  
16. [Glossaire](#16-glossaire)

---

## 1. Vision et objectifs

### 1.1 Vision

Permettre à des utilisateurs non développeurs (étudiants, collaborateurs labo) de **concevoir, tester et lancer** une manipulation complète — vidéos, sons, stimuli générés, questionnaires, triggers matériels — **sans éditer du code Python** pour les blocs standards, via un **protocole JSON unique** et une interface graphique, en choisissant pour chaque étape le **moteur le plus adapté** parmi Qt, Pygame et PsychoPy.

Pour les besoins avancés (comme **OpenSesame → inline_script**), le même protocole peut **enchaîner des tâches Python** définies dans des fichiers `.py` du projet, appelées comme n’importe quel autre nœud.

### 1.2 Principe multi-moteurs (exigence structurante)

The Kit n’est **pas** un fork d’Arôme : c’est un **orchestrateur** qui unifie des briques déjà éprouvées dans vos dépôts labo.

| Moteur | Rôle typique | Origine dans vos outils |
|--------|--------------|-------------------------|
| **Qt (PyQt6)** | UI expérimentateur, questionnaires, vidéo « simple », éditeur de protocole, coquille applicative | Arôme, Projet Arôme |
| **Pygame** | Stimuli génératifs temps réel, plein écran, MOT, occultation, flux optique | randomflow, shadowi, MOT, occultation |
| **PsychoPy** | Précision temporelle affichage, routines, photosonde ; peut s’appuyer sur la couche low-latency pour l’audio | audi_visuel, P1-P9, occultation Action |
| **Python (inline)** | Tâches codées sur mesure ; intégration orchestrateur + API session | OpenSesame `inline_script`, scripts labo P1-P9 |

**Couche audio low-latency (transverse)** — indépendante du moteur d’affichage :

| Composant | Rôle | Origine |
|-----------|------|---------|
| **sounddevice + PortAudio** | Lecture audio en **callback** ; horloge **`time.perf_counter()`** ; planification buffer | `manip_psychophysique_json`, audi_visuel |
| **API hôte OS** (sélection auto ou forcée) | **Windows WASAPI** (priorité), WDM-KS, DirectSound ; **macOS Core Audio** ; **Linux ALSA**, JACK, Pulse | P1-P9 `choose_device_os_aware` |

Ce n’est pas un 4ᵉ moteur d’écran : c’est un **`timing_mode`** (ou `audio_backend`) activable sur les nœuds `audio`, `av_sync`, et essais PsychoPy/Pygame qui exigent une sync millimétrique.

**Règles :**

1. Chaque nœud porte un champ **`engine`** : `"qt"` | `"pygame"` | `"psychopy"` | `"python"` (tâche inline).
2. Les nœuds avec exigence temporelle portent **`timing_mode`** : `"standard"` | `"low_latency"` (défaut selon type ; voir § 4.5).
3. Un même protocole peut **enchaîner** moteurs et modes (ex. consigne Qt → flux optique Pygame → `av_sync` PsychoPy + **low_latency** WASAPI → QCM Qt).
4. L’éditeur guide le choix moteur + mode timing sans connaître PortAudio/WASAPI.
5. Profils pip : moteurs d’affichage + **`requirements-lowlatency.txt`** (`sounddevice`, `soundfile`, `numpy`) — voir F-904.

### 1.3 Objectifs produit

| # | Objectif | Mesure de succès |
|---|----------|------------------|
| O1 | Protocole JSON unique, indépendant du moteur | Chargement `.json` sans modifier le code ; champ `engine` par nœud |
| O2 | Les trois moteurs sont utilisables dans une même session | Protocole de démo avec au moins 1 nœud Qt + 1 Pygame + 1 PsychoPy |
| O3 | Régression sur l’exemple Arôme (moteur Qt) | `experiment.json` et variantes 1–9 rejouables via adaptateur |
| O4 | Porter les briques des autres outils ROSITO | Capabilities par moteur (voir § 4.3) couvertes progressivement |
| O5 | Traçabilité des données | CSV/JSON horodatés ; colonne `engine` dans les logs |
| O6 | Déploiement poste labo | macOS / Windows / Linux ; venv/profils par combinaison de moteurs |
| O7 | **Audio/vidéo low-latency** au niveau P1-P9 | PortAudio + hôte OS natif (WASAPI, Core Audio, ALSA…) ; jitter cible documenté ; logs `*_perf` |
| O8 | **Reproductibilité scientifique** | Protocole versionné, hash assets, journal session immuable |
| O9 | **Utilisable offline** | Aucune dépendance réseau en run participant |
| O10 | **Extensible** | Nouveaux types de nœuds / handlers pygame sans fork du cœur |
| O11 | **Catalogue visuel complet** | Vidéo, image, formes et scènes générées documentés et sélectionnables dans l’éditeur |
| O12 | **Tâches Python inline** (type OpenSesame) | Nœud JSON → fichier `.py` ; `prepare`/`run` ; accès API session |

### 1.4 Indicateurs de succès (KPI)

| KPI | Cible v1 | Mesure |
|-----|----------|--------|
| Temps création protocole simple (vidéo + QCM) | &lt; 15 min sans code | Test utilisateur expérimentateur |
| Taux échec lancement session | &lt; 5 % sur poste labo référence | Logs `check-engines` / `check-audio` |
| Régression Arôme | 100 % variantes `experiment1-9*.json` | Suite auto import |
| Jitter A/V (poste calibré, low_latency) | &lt; 10 ms (objectif P1-P9) | Essai forward+WAV + photosonde |
| Complétude export | 100 % essais ont `subject_id`, `node_id`, horodatage | Validation schéma session |

### 1.5 Non-objectifs (v1)

- Remplacer PsychoPy **Builder** ou OpenSesame (The Kit **exécute** via l’API/runtime PsychoPy, sans imposer Builder)
- Analyse statistique intégrée (R, SPSS, Jupyter) — **export** vers pipelines externes seulement
- Hébergement cloud multi-utilisateurs / base de données centrale / sync temps réel
- Stimulation **entrante** TMS / Neuroconn / NiDaq en boucle fermée — hors scope (triggers **sortants** OK)
- Enregistrement vidéo participant (webcam) — hors scope (projet `stream` séparé)
- Conformité dispositif médical certifié CE/FDA — logiciel de recherche non clinique par défaut
- Support mobile / tablette participant

### 1.6 Principes de conception

1. **Offline-first** — protocole + assets en dossier local ; run sans Internet.  
2. **Explicit over magic** — `engine` et `timing_mode` visibles dans JSON et logs.  
3. **Fail loud** — erreur média, moteur manquant, WASAPI fallback → message actionnable.  
4. **Same clock** — `perf_counter` pour corrélation audio/vidéo/triggers en mode low_latency.  
5. **Import, don’t rewrite** — porter P1-P9 / Arôme avant de réécrire.  
6. **Session sacrée** — une fois lancée, données participant jamais écrasées silencieusement.

---

## 2. Référence de départ — Projet Arôme (exemple, pas le produit)

Arôme est le **point de départ le plus riche** (protocole JSON, vidéo, QCM, triggers, `wait_key`). The Kit **réutilise et généralise** ce modèle en y ajoutant Pygame et PsychoPy comme citoyens de première classe.

### 2.1 Stack Arôme v0

- **Python ≥ 3.8**, **PyQt6**, `QMediaPlayer` + `QVideoWidget`
- Protocole : fichier JSON (`nodes[]`, `loop`)
- Sortie : `data/reponses_YYYYMMDD_HHMMSS.csv`
- Trigger : nœud `trigger` (série COM) + `wait_key` (touche **t**, compatible Arduino `triggerAnaelle/`)

### 2.2 Types de nœuds existants

| Type | Champs clés | Comportement |
|------|-------------|--------------|
| `video` | `file`, `time` (s) | Lecture vidéo, timer fixe puis suite |
| `questionnaire` | `question1`…`question7`, `echelle[]` | Sliders + « Je ne sais pas », auto-submit 60 s |
| `trigger` | `port`, `value` | Écriture byte sur port série |
| `wait_key` | `key`, `message` | Attente touche avant suite |

### 2.3 Limites Arôme v0 → adressées par The Kit

- Moteur unique (Qt) → **orchestration Qt + Pygame + PsychoPy**
- Chargement du JSON **hardcodé** dans `main` → CLI + éditeur
- CSV incomplet → schéma session unifié + colonne `engine`
- Pas de sync A/V précise → nœuds `engine: psychopy` (audi_visuel / P1-P9)
- Pas de stimuli génératifs → nœuds `engine: pygame`
- EyeLink / LSL / photosonde → modules optionnels transverses (tous moteurs)

---

## 3. Personas et cas d’usage

| Persona | Besoin | Exemple |
|---------|--------|---------|
| **Expérimentateur** | Monter un protocole du jour sans dev | Arôme : 4 conditions × (vidéo + QCM + trigger) |
| **Technicien labo** | Calibrer A/V, choisir sortie audio, tester triggers | Reprendre workflow `audi_visuel` |
| **Développeur** | Étendre par nouveaux types de nœuds | Plugin / module stimulus |
| **Participant** | Interface simple, pas de distraction | Plein écran, instructions claires |
| **Analyste** | Fichiers exploitables | CSV + JSON session, horodatage ms |
| **Responsable données** | RGPD / traçabilité | Pseudonymisation `subject_id`, pas de données santé par défaut |

### 3.1 Parcours types

| Parcours | Étapes | Mode |
|----------|--------|------|
| **A. Arôme classique** | Accueil sujet → vidéos → QCM → triggers série | `engine: qt`, `standard` |
| **B. Psycho A/V précis** | Instructions → `av_sync` low_latency → réponse clavier | psychopy/pygame + **LL** |
| **C. Oculométrie** | Calib EyeLink → blocs pygame → fin EDF | pygame + EyeLink P3 |
| **D. Calibration labo** | `check-audio` → test photosonde → ajustement `offset_ms` | outil technicien |
| **E. Conception** | Template → éditeur → validation → export zip → transfert poste | Concepteur Qt |

---

## 4. Architecture cible (conceptuelle)

### 4.1 Vue d’ensemble

```text
┌─────────────────────────────────────────────────────────────┐
│  Mode Concepteur — coquille Qt                              │
│  - Éditeur protocole, choix moteur par nœud                 │
│  - Bibliothèque médias / presets / validation               │
└──────────────────────────┬──────────────────────────────────┘
                           │ protocol.json (+ assets/)
┌──────────────────────────▼──────────────────────────────────┐
│  Orchestrateur The Kit (agnostique moteur)                  │
│  - Parse protocole, cycle de vie nœud, logging, I/O         │
│  - Charge scripts/*.py (python_task)                        │
└─┬─────────┬─────────┬─────────┬───────────────────────────┘
  │         │         │         │
  ▼         ▼         ▼         ▼
┌──────┐ ┌──────┐ ┌────────┐ ┌──────────────────┐
│ Qt   │ │Pygame│ │PsychoPy│ │ Engine Python    │
│ UI   │ │ RT   │ │ timing │ │ prepare() / run()│
└──────┘ └──────┘ └────────┘ └──────────────────┘
         └────────────────┬───────────────┘
                          ▼
              I/O transverse : série, LSL, EyeLink, clavier

┌─────────────────────────────────────────────────────────────┐
│  Couche Audio Low-Latency (optionnelle, transverse)         │
│  sounddevice → PortAudio → WASAPI / Core Audio / ALSA…      │
│  callbacks, blocksize, perf_counter, offset_ms              │
└─────────────────────────────────────────────────────────────┘
         ▲ utilisée par av_sync, audio, psychopy_routine, etc.
```

### 4.2 Contrat orchestrateur ↔ moteur

Chaque moteur implémente la même interface logique :

| Méthode / événement | Description |
|---------------------|-------------|
| `prepare(node, context)` | Préchargement assets, vérif deps |
| `run(node, context) → NodeResult` | Exécution bloquante jusqu’à fin du nœud |
| `abort()` | Arrêt d’urgence (touche expérimentateur) |
| `capabilities()` | Liste des `node.type` supportés |

`NodeResult` : `{ status, responses?, rt_ms?, markers?, engine_version? }` — format unique pour le logger.

**Moteur Python (`engine: python`)** — même contrat, implémenté par `the_kit.engines.python_engine` :

| Phase | Fonction script (obligatoire / optionnelle) | Rôle |
|-------|---------------------------------------------|------|
| **prepare** | `def prepare(ctx) -> None` | Préchargement, init matériel, vérifs (1× par nœud/session selon config) |
| **run** | `def run(ctx) -> NodeResult \| dict` | Tâche principale pendant l’essai |

Le fichier est chargé depuis **`{protocol_root}/scripts/`** uniquement (pas de chemin arbitraire hors protocole).

### 4.3 Répartition indicative type de nœud → moteur

| Type de nœud | Famille §4.9 | Moteur par défaut | Alternatif |
|--------------|------------|-------------------|------------|
| `video`, `image`, `slideshow` | A fichier | **qt** | psychopy (frame-accurate) |
| `av_sync` | A + audio | **psychopy** + low_latency | qt/pygame + PortAudio |
| `shapes`, `fixation`, `psychopy_stim` | B généré | **psychopy** | pygame |
| `optic_flow`, `mot`, `shadow_ball`, `occultation` | B scène labo | **pygame** | — |
| `occultation_ttc`, `psychopy_routine` | B | **psychopy** | pygame |
| `pygame_scene` | B custom | **pygame** | — |
| `instructions`, `questionnaire`, `wait_key` | C UI | **qt** | — |
| `blank`, `photosonde_square` | C overlay | psychopy / pygame | qt |
| `keyboard_response` | D (souvent après B/A) | **pygame** | psychopy |
| `audio` | — | psychopy + low_latency | — |
| **`python_task`** | E inline | **`python`** | — |
| `trigger`, `delay` | — | orchestrateur | — |

L’éditeur peut **surcharger** le défaut (`engine` explicite dans le JSON).

### 4.4 Intégration technique des trois moteurs

| Moteur | Mode d’intégration prévu | Contrainte |
|--------|--------------------------|------------|
| **Qt** | Application principale ; fenêtre participant ou embed | Thread UI principal |
| **Pygame** | Fenêtre dédiée plein écran **ou** surface embarquée (P2) ; handoff focus clavier | `SDL_VIDEO_WINDOW_POS`, multi-écran |
| **PsychoPy** | `psychopy.visual.Window` dédiée par nœud ou session ; subprocess isolé si conflit deps (P2) | Version figée type 2023.1.x (audi_visuel) ; venv séparé recommandé |

**Principe** : un seul schéma `protocol_version` ; chaque nœud a `type` + **`engine`** + option **`timing_mode`**.

### 4.5 Couche audio low-latency (référence P1-P9)

Objectifs de jitter observés dans vos docs (à valider sur chaque poste) :

| Contexte | Cible indicative | Référence |
|----------|------------------|-----------|
| Psychophysique labo (A/V) | Jitter matériel **&lt; 5–10 ms** ; logiciel **2–3 ms** | `OPTIONS_JITTER_5MS.md`, `ANTI_JITTER_METHODS.md` |
| IRM (sync TR) | **&lt; 1 ms** (pipeline dédié hors The Kit v1) | `P1-P9.py` |
| Linux labo | **3–5 ms** avec sounddevice + ALSA | `LINUX_AUDIO_OPTIONS.md` |

**Stack technique à porter depuis `manip_psychophysique_json/main.py` :**

| Mécanisme | Description |
|-----------|-------------|
| **PortAudio via sounddevice** | `OutputStream` en callback ; pas de lecture « fire-and-forget » pour les essais critiques |
| **Sélection hôte OS** | Windows : préférence **WASAPI** → WDM-KS → MME → DirectSound ; macOS : **Core Audio** ; Linux : ALSA / JACK / Pulse |
| **`audio_device_index`** | Index PortAudio explicite (`python -m sounddevice`) — priorité absolue |
| **`audio_device_query`** | Sous-chaîne dans nom périphérique + host API |
| **`blocksize`** | Taille buffer callback (ex. 64–128 frames) — compromis latence / dropouts |
| **`output_sample_rate`** | Taux flux sortie ; rééchantillonnage WAV si besoin (Windows souvent 44100/48000) |
| **`offset_ms`** | Décalage audio vs début logique stimulus |
| **`scheduling_lead_s`** | Marge de planification avant `trial_start_perf` (ex. 0.2–0.35 s) |
| **Horloge unique** | `time.perf_counter()` pour planification audio **et** premier flip vidéo |
| **`outputBufferDacTime`** | Estimation début réel DAC dans le callback (quand disponible) |
| **Logs essai** | `audio_target_start_perf`, `audio_actual_start_perf`, `video_first_flip_perf`, `audio_hostapi` |
| **Anti-jitter** | Buffers pré-alloués, blocksize minimal, option CPU affinity, buffer pygame 64 (si mix pygame+audio) | `ANTI_JITTER_METHODS.md` |
| **Photosonde** | Carré blanc coin écran + corrélation timestamps pour calibration ms | audi_visuel, P1-P9 |

**Modes d’usage dans The Kit :**

| `timing_mode` | Comportement |
|---------------|--------------|
| `standard` | Qt `QMediaPlayer`, PsychoPy audio par défaut, pygame.mixer — suffisant questionnaires / vidéos longues |
| `low_latency` | Module **`the_kit.audio.low_latency`** (port ScheduledAudioPlayer P1-P9) ; obligatoire pour `av_sync` « labo » et export métriques sync |

### 4.6 Modèle expérimental (au-dessus des nœuds)

Les **nœuds** restent l’unité d’exécution ; le PRD ajoute une couche optionnelle **trial-oriented** (comme P1-P9 / randomflow) pour les designs complexes :

```text
Protocol
├── metadata (name, version, ethics_id?)
├── presentation   (randomize, seed, counterbalance)
├── display        (fullscreen, screen_index, gamma_linear?)
├── audio_defaults (timing_mode, blocksize, …)
├── conditions[]   (id, label, stimulus refs, repetitions)
└── nodes[]        (séquence linéaire OU générée depuis conditions)
```

| Concept | JSON / comportement | Priorité |
|---------|---------------------|----------|
| **Condition** | `conditions[]` avec `id`, `video`, `audio`, `repetitions` | P2 |
| **Essai (trial)** | Expansion conditions → liste d’essais ; shuffle | P2 |
| **Bloc** | Groupe de nœuds ou d’essais ; pause inter-bloc | P2 |
| **Counterbalancing** | `random_seed` + `randomize_trials` + grilles Latin square (P3) | P2–P3 |
| **ITI** | `iti_jitter_s: [min, max]` entre essais | P2 |
| **Practice / main** | Flag session ou préfixe protocole | P2 |

Si absent : comportement **linéaire** actuel (liste `nodes` uniquement, comme Arôme v0).

### 4.7 Affichage, multi-écran et rafraîchissement

| Paramètre | Description | Source |
|-----------|-------------|--------|
| `display.fullscreen` | Plein écran participant | P1-P9, MOT_Tunnel |
| `display.screen_index` | Moniteur participant (0, 1, …) | manip JSON |
| `SDL_VIDEO_WINDOW_POS` | Position fenêtre pygame (ex. écran 2) | MOT_Tunnel |
| `winType` / unités PsychoPy | `pix`, `norm`, `height` — documenter choix par protocole | psychopy |
| **V-Sync / refresh** | Documenter taux Hz mesuré ; option désactiver vsync pour latence (avancé, risqué) | P3 |
| **Taille stimulus** | Degrés visuels ou pixels — paramètre par scène pygame (shadowi) | P3 |
| **Mode miroir expérimentateur** | Fenêtre preview non plein écran sur écran 0 (Concepteur / run debug) | P2 |

### 4.8 Package session (artefacts disque)

Structure cible d’une session (`sessions/20260522_S012_143022/`) :

```text
session/
├── protocol.json              # copie au lancement (hash SHA-256 en metadata)
├── protocol.hash
├── environment.json           # versions Python, the_kit, engines, host API audio
├── events.jsonl               # un événement par ligne (append-only)
├── responses.csv              # réponses comportementales
├── sync_trials.json           # essais low_latency (*_perf)
├── logs/the_kit.log
├── assets/                    # lien ou copie médias utilisés (option P2)
└── eyetrack/                   # EDF / sidecars (P3)
```

### 4.9 Présentation visuelle (taxonomie)

Tout ce que le **participant voit** à l’écran est un **stimulus visuel**. The Kit distingue **quatre familles** (indépendantes de l’audio et des questionnaires) :

```text
                    PRÉSENTATION VISUELLE
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   A. Fichiers            B. Généré            C. UI / overlay
   (assets)              (temps réel)           (pas un « essai »)
        │                     │                     │
   video                  shapes_primitives      fixation
   image                  optic_flow             instructions
   slideshow              mot / balls            photosonde_square
   av_sync (piste         shadow_ball            blank / iti
    vidéo)                 occultation
                          psychopy_stim
                          pygame_scene (custom)
        │
   D. Composite
   av_sync = vidéo fichier + calage frame ;
   trial = stimulus visuel + keyboard_response
```

#### A. Stimuli visuels issus de fichiers

| Type nœud | Contenu affiché | Moteur(s) | Référence labo |
|-----------|-----------------|-----------|----------------|
| **`video`** | Séquence MP4/MOV, durée fixe ou fin fichier | **qt** (QMediaPlayer), **psychopy** (MoviePy frames), OpenCV (P2) | Arôme, P1-P9, opticflow_Alba |
| **`image`** | PNG/JPG plein écran ou centrée | qt, psychopy, pygame | P1-P9 `BlackScreenCross` |
| **`slideshow`** | Liste d’images + durée par slide | qt ou psychopy | — |
| **`av_sync`** | **Piste vidéo** synchronisée à l’audio (fichier vidéo + WAV séparé) | psychopy / pygame / qt + **low_latency** pour l’audio | audi_visuel, manip JSON |

Champs JSON communs : `file` ou `files[]`, `duration_s`, `fit` (`contain` | `cover` | `native`), `background_color` (ex. `#000000`).

#### B. Stimuli visuels générés (formes & scènes)

Pas de fichier vidéo/image : le moteur **dessine** chaque frame.

| Type nœud | Contenu généré | Moteur | Référence labo |
|-----------|----------------|--------|----------------|
| **`shapes`** | Primitives paramétriques : cercle, rectangle, ellipse, croix, ligne, grille, damier | pygame ou psychopy | base pour fixation / calib |
| **`optic_flow`** | Nuage de points (cohérence, bruit brownien / inverse) | **pygame** | randomflow |
| **`mot`** | Balles MOT, masque, trajectoires | **pygame** | MOT, MOT_Tunnel |
| **`shadow_ball`** | Balle + ombre, perspective, couloir | **pygame** | shadowi |
| **`occultation`** | Balle + occulteur, options cercle timing | **pygame** | occultation |
| **`occultation_ttc`** | Trajectoires TTC (matrice JSON) | pygame ou **psychopy** | occ_action_psychopy |
| **`psychopy_stim`** | Params type Builder : text, grating, image en RAM, polygon | **psychopy** | générique |
| **`pygame_scene`** | Handler externe enregistré (clé → module) | **pygame** | extensibilité E-007 |

Champs JSON communs : bloc **`visual`** ou **`params`** avec dimensions, couleurs RGB, vitesse, durée, position, `dot_number`, etc.

**Exemple `shapes` (fixation + stimulus simple) :**

```json
{
  "id": "fix_cross",
  "type": "shapes",
  "engine": "psychopy",
  "duration_s": 1.0,
  "visual": {
    "elements": [
      { "shape": "cross", "size_px": 20, "color": [255, 255, 255], "line_width": 2 }
    ],
    "background": [0, 0, 0]
  }
}
```

**Exemple scène générée (flux optique) :** voir §6.2 nœud `optic_flow`.

#### C. Overlays et écrans non-stimulus

| Type nœud | Rôle visuel | Moteur |
|-----------|-------------|--------|
| **`fixation`** | Point ou croix de fixation (sous-type de `shapes` ou nœud dédié) | qt / psychopy / pygame |
| **`instructions`** | Texte / markdown rendu plein écran | **qt** |
| **`blank`** | Écran uni (souvent noir) — ITI, handoff moteurs | tous |
| **`photosonde_square`** | Flash blanc coin écran (calibration ms) | psychopy / pygame (couche overlay) |
| **`questionnaire`** | Formulaires, sliders (UI participant) | **qt** |

#### D. Combinaisons courantes

| Pattern | Nœuds visuels enchaînés |
|---------|-------------------------|
| Arôme | `instructions` → `wait_key` → **`video`** × N → **`questionnaire`** |
| Looming labo | `fixation` → **`av_sync`** (vidéo + audio) → `keyboard_response` |
| Perception mouvement | `fixation` → **`optic_flow`** ou **`shadow_ball`** → réponse |
| MOT | `fixation` → **`mot`** (pygame + EyeLink P3) |

#### Choix moteur pour l’affichage (rappel)

| Besoin visuel | Moteur recommandé |
|---------------|-------------------|
| Vidéo longue, protocole simple | **qt** |
| Sync frame + vidéo fichier | **psychopy** |
| Animation 60 FPS, centaines d’objets | **pygame** |
| Gratings / stimuli psycho classiques | **psychopy** |
| Primitives simples, fixation | **psychopy** ou **pygame** |
| Logique custom, matériel atypique, glue code | **`python_task`** |

### 4.10 Tâches Python inline (type OpenSesame)

Comme le composant **inline_script** d’[OpenSesame](https://osdoc.cogsci.nl/) : une étape du protocole exécute du **code Python** fourni par l’équipe, sans modifier le cœur de The Kit.

#### Positionnement

| OpenSesame | The Kit |
|------------|---------|
| Item **inline_script** avec onglets Prepare / Run | Nœud **`python_task`** + fichier `scripts/*.py` |
| Variables `var.*` | **`ctx.variables`** (dict persistant pendant la session) |
| `self.*` devices exp | **`ctx.devices`** (audio, display, serial, eyetrack…) |
| Séquence visuelle dans l’UI | Séquence dans **`nodes[]`** du JSON |

#### Structure dossier protocole

```text
mon_experience/
├── protocol.json
├── scripts/
│   ├── __init__.py          # optionnel
│   ├── send_cedrus.py       # tâche isolée
│   └── custom_stimulus.py   # peut dessiner via ctx.display
├── videos/
├── audio/
└── data/                    # créé à l’exécution
```

#### Nœud JSON (`python_task`)

```json
{
  "id": "prep_eyelink_messages",
  "type": "python_task",
  "engine": "python",
  "label": "Config messages EyeLink",
  "script": {
    "file": "scripts/eyelink_setup.py",
    "prepare": "prepare",
    "run": "run",
    "args": {
      "calibration": "HV5",
      "drift_correction": true
    }
  },
  "timeout_s": 120,
  "on_error": "abort"
}
```

| Champ `script` | Description |
|----------------|-------------|
| `file` | Chemin **relatif** au dossier protocole (obligatoire sous `scripts/`) |
| `prepare` | Nom de la fonction prepare (défaut : `prepare` si présente, sinon skip) |
| `run` | Nom de la fonction run (défaut : `run`) |
| `args` | Dict fusionné dans `ctx.params` pour ce nœud |

#### API `TaskContext` exposée aux scripts

Objet **`ctx`** passé à `prepare(ctx)` et `run(ctx)` :

| Membre | Description |
|--------|-------------|
| `ctx.protocol_path` | Dossier racine du protocole |
| `ctx.session_dir` | Dossier session en cours |
| `ctx.subject_id` | Identifiant participant |
| `ctx.node_id`, `ctx.node_index` | Nœud courant |
| `ctx.params` | `args` du JSON + surcharge |
| `ctx.variables` | Magasin clé/valeur **persistant** entre nœuds `python_task` et lisible par l’orchestrateur (export log) |
| `ctx.log.event(name, **payload)` | Écriture `events.jsonl` |
| `ctx.log.marker(code, t_perf=None)` | Marqueur timing (LSL futur) |
| `ctx.trigger.serial(port, value)` | Équivalent nœud `trigger` |
| `ctx.audio` | Accès couche low_latency si dispo (jouer WAV, planifier) |
| `ctx.display` | Handle fenêtre active (pygame/psychopy/qt) si moteur déjà ouvert ; sinon `None` |
| `ctx.wait_keys(keys, timeout_s)` | Attente clavier participant |
| `ctx.get_engine(name)` | `"pygame"` \| `"psychopy"` \| `"qt"` — instance si initialisée |

**Retour `run` :** dict ou `NodeResult` avec `status: "ok"|"error"|"skip"`, `responses`, `rt_ms`, `data` (JSON-serializable pour CSV).

#### Exemple minimal `scripts/hello.py`

```python
from the_kit.task_api import NodeResult

def prepare(ctx):
    ctx.variables["trial_count"] = 0

def run(ctx):
    ctx.variables["trial_count"] += 1
    ctx.log.event("custom_hello", count=ctx.variables["trial_count"])
    return NodeResult(status="ok", data={"count": ctx.variables["trial_count"]})
```

#### Règles de sécurité et confiance

| Règle | Détail |
|-------|--------|
| **Pas de code dans le JSON** | Le JSON référence un **fichier** ; interdit `exec(string)` depuis champs protocole (F-1501) |
| **Sandbox chemins** | Seuls les `.py` sous `{protocol}/scripts/` sont importables |
| **Confiance labo** | Code exécuté avec les **droits utilisateur** du poste (comme OpenSesame) — pas de sandbox OS v1 |
| **Avertissement UI** | L’éditeur affiche « protocole contient du Python personnalisé » |
| **Dry-run** | Exécute `prepare` + analyse statique légère (import connu) sans participant |

#### Quand utiliser `python_task` vs autres extensions

| Besoin | Préférer |
|--------|----------|
| Stimulus visuel standard | Nœuds §4.9 (`video`, `optic_flow`, …) |
| Handler pygame réutilisable | `pygame_scene` + registre F-1601 |
| **Script one-shot**, glue, matériel exotique | **`python_task`** |
| Toute la logique d’essai en code | Fichier `.py` + un seul nœud ou CLI hors The Kit |

---

## 5. Exigences fonctionnelles

Légende priorité : **P0** = indispensable v1 · **P1** = v1.x proche · **P2** = v2 · **P3** = option / labo avancé

### 5.0 Moteurs Qt, Pygame, PsychoPy (exigences transverses)

| ID | Fonctionnalité | Priorité | Note |
|----|----------------|----------|------|
| E-001 | Champ obligatoire `engine` sur chaque nœud (ou défaut explicite dans le schéma) | P0 | `qt` \| `pygame` \| `psychopy` |
| E-002 | Registre des moteurs : détection à l’install (quel moteur est disponible) | P0 | Au lancement |
| E-003 | Refus de lancer un nœud si moteur absent → message clair + lien doc profil pip | P0 | — |
| E-004 | Protocole multi-moteurs : handoff fenêtre / focus / résolution entre nœuds consécutifs | P1 | Qt ↔ Pygame ↔ PsychoPy |
| E-005 | Colonne `engine` dans tous les exports de session | P0 | — |
| E-006 | Nœud `psychopy_routine` : exécution d’une routine paramétrée (JSON) sans Builder obligatoire | P2 | P1-P9, audi_visuel |
| E-007 | Nœud `pygame_scene` : dispatch vers handler enregistré (optic_flow, mot, …) | P1 | Extensibilité |
| E-008 | Documentation par moteur : quand choisir Qt vs Pygame vs PsychoPy (aide intégrée) | P1 | — |
| E-009 | Tests de fumée par moteur (`the_kit check-engines`) | P1 | Comme `check_dependencies.py` |

### 5.1 Cœur protocole et orchestrateur

| ID | Fonctionnalité | Priorité | Source / note |
|----|----------------|----------|---------------|
| F-001 | Charger un protocole JSON via argument CLI (`--protocol`) ou dialogue fichier | P0 | Arôme |
| F-002 | Métadonnées protocole : `name`, `version`, `description`, `loop`, `randomize_nodes` | P0 | randomflow, P1-P9 |
| F-003 | Métadonnées session : `subject_id`, `session_id`, `experimenter`, date | P0 | Pattern labo MEMORY |
| F-004 | Orchestration séquentielle des nœuds avec gestion d’erreur (média manquant → message + skip configurable) | P0 | Arôme |
| F-005 | Boucles de protocole (`loop`) + option shuffle des blocs conditionnels | P1 | Arôme + randomflow |
| F-006 | Pause / abort expérience (touche expérimentateur secrète) | P1 | MOT, shadowi |
| F-007 | Écran instructions début / fin (texte markdown ou HTML léger) | P1 | — |
| F-008 | Mode « practice » vs « main » (même protocole, flag dans logs) | P2 | P1-P9 |

### 5.2 Présentation visuelle (stimulus à l’écran)

> Taxonomie complète : **§4.9**. Audio : §5.3 · Affichage matériel (écran, Hz) : §5.12.

#### 5.2.A Stimuli visuels — fichiers (vidéo, image)

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| V-001 | Nœud **`video`** : fichier local, `duration_s`, fond noir entre clips | P0 | Arôme |
| V-002 | Nœud **`image`** : PNG/JPG, durée, centrage, `fit` contain/cover | P1 | P1-P9 |
| V-003 | Nœud **`slideshow`** : `images[]` + `duration_s` par slide ou global | P2 | — |
| V-004 | **`av_sync`** : affichage **piste vidéo** fichier + sync audio (voir aussi F-202) | P1 | audi_visuel |
| V-005 | Préchargement frame / buffer vidéo suivant (psychopy MoviePy / qt) | P1 | F-108 |
| V-006 | `engine: psychopy` sur `video` / `av_sync` — flip frame-accurate, log `video_first_flip_perf` | P1 | manip JSON |
| V-007 | `engine: qt` sur `video` — QMediaPlayer (mode standard, protocoles Arôme) | P0 | Arôme |
| V-008 | Fallback **`playvideo`** OpenCV plein écran si qt indisponible | P2 | opticflow_Alba |
| V-009 | Boucle vidéo si `duration_s` &gt; durée fichier (option `loop: true`) | P2 | P1-P9 |
| V-010 | Aperçu miniature vidéo/image dans l’éditeur (Concepteur) | P2 | O11 |

#### 5.2.B Stimuli visuels — formes et scènes générées

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| V-101 | Nœud **`shapes`** : liste `elements[]` (circle, rect, ellipse, cross, line, grid, checkerboard) | P1 | base labo |
| V-102 | Paramètres forme : `color` RGB, `size_px` ou `size_norm`, `position`, `line_width`, `fill` | P1 | psychopy Units |
| V-103 | Nœud **`fixation`** (raccourci) : croix ou point, durée, couleur — alias de `shapes` | P1 | shadowi, P1-P9 |
| V-104 | Nœud **`optic_flow`** : params randomflow (`dot_coherence`, `noise_mode`, …) | P2 | randomflow |
| V-105 | Nœud **`mot`** : nb cibles, vitesse, masque scotome (preset MOT) | P3 | MOT_Tunnel |
| V-106 | Nœud **`shadow_ball`** : conditions ombre (congruente / incongruente / fixe) | P3 | shadowi |
| V-107 | Nœud **`occultation`** : occulteur, cercle 0/1/2, vitesses | P3 | occultation |
| V-108 | Nœud **`occultation_ttc`** : matrice trajectoires JSON | P3 | occ_action |
| V-109 | Nœud **`psychopy_stim`** : type `text` \| `grating` \| `image` \| `polygon` + champs PsychoPy | P2 | psychopy |
| V-110 | Nœud **`pygame_scene`** : `handler: "optic_flow"` → registre handlers | P1 | E-007 |
| V-111 | Rendu **60 FPS** cible pour scènes pygame (flux optique, MOT) | P2 | NF-06 |
| V-112 | Mode **degrés visuels** (`size_deg`, distance viewing cm) en plus des pixels | P3 | shadowi |
| V-113 | **`blank`** : écran couleur unie `duration_s` (ITI, transition moteurs) | P1 | handoff |
| V-114 | Overlay **`photosonde_square`** : position, taille, durée flash (sans nœud vidéo) | P1 | P1-P9 |
| V-115 | Superposition overlay sur stimulus (photosonde par-dessus vidéo/pygame) | P2 | audi_visuel |

#### 5.2.C Éditeur — catalogue visuel

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| V-201 | Palette « Ajouter stimulus » : **Vidéo · Image · Forme · Scène labo · Fixation · Vide** | P1 | O11 |
| V-202 | Aperçu un frame / une frame vidéo avant run | P2 | — |
| V-203 | Assistant choix moteur selon type visuel (arbre décision §4.9) | P1 | E-008 |
| V-204 | Galerie presets scènes : optic flow, looming (vidéo), ombre, MOT | P2 | templates |

#### 5.2.D Exigences héritées (affichage lié au visuel)

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-102 | Plein écran participant (second écran optionnel) | P0 | §5.12 F-120* |
| F-104 | Fixation avant/après stimulus (via `fixation` ou `shapes`) | P1 | shadowi |
| F-107 | Diaporama (= `slideshow` V-003) | P2 | — |
| F-108 | Préchargement média visuel suivant | P1 | V-005 |
| F-109 | (= V-006) Vidéo psychopy frame-accurate | P1 | audi_visuel |

### 5.3 Audio (standard et low-latency)

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-201 | Nœud `audio` : fichier WAV, durée ; `timing_mode` standard ou low_latency | P1 | P1-P9 |
| F-202 | Nœud `av_sync` : vidéo + WAV séparé ; `offset_ms` ; sync via perf_counter | P1 | manip_psychophysique_json |
| F-203 | Choix périphérique : liste PortAudio (`python -m sounddevice`) | P1 | P1-P9 |
| F-204 | Réglage volume par nœud et global | P1 | Arôme |
| F-205 | Assistant calibration A/V (offset_ms + mesure photosonde / oscilloscope externe) | P2 | audi_visuel |
| F-206 | `av_sync` + `timing_mode: low_latency` : moteur affichage (psychopy/pygame/qt) + **audio PortAudio** | P0 | Cœur P1-P9 |
| F-207 | Presets looming/receding (forward/backward + WAV) | P2 | P1-P9 |

### 5.3b Audio low-latency — PortAudio / WASAPI et équivalents

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| LL-001 | Module `timing_mode: low_latency` basé sur **sounddevice** (callbacks) | P0 | `ScheduledAudioPlayer` P1-P9 |
| LL-002 | Sélection **Host API** OS : WASAPI (Windows), Core Audio (macOS), ALSA/JACK (Linux) | P0 | `choose_device_os_aware` |
| LL-003 | Paramètres JSON section `audio` : `audio_device_index`, `audio_device_query`, `blocksize`, `output_sample_rate`, `sample_rate`, `offset_ms`, `scheduling_lead_s` | P0 | README manip_psychophysique_json |
| LL-004 | Horloge session **`time.perf_counter()`** pour audio + premier flip vidéo | P0 | P1-P9 |
| LL-005 | Logs essai : `audio_hostapi`, `audio_device_index`, `audio_target_start_perf`, `audio_actual_start_perf`, `video_first_flip_perf` | P1 | P1-P9 |
| LL-006 | Estimation `audio_actual_start` via `outputBufferDacTime` dans callback | P1 | `P1-P9_oscilloscope_test_precise.py` |
| LL-007 | Préchargement / planification buffer audio avant `trial_start_perf` | P1 | scheduling_lead_s |
| LL-008 | Rééchantillonnage WAV à `output_sample_rate` si différent du natif | P1 | Windows WASAPI |
| LL-009 | Diagnostic : `the_kit check-audio` — liste host APIs, latences suggérées, device par défaut | P1 | `diagnostic_audio.py` |
| LL-010 | Mode test sync : boucle photosonde + bip (sans protocole complet) | P2 | oscilloscope tests P1-P9 |
| LL-011 | Document « choix blocksize » (64 vs 128 vs 256) et risque dropouts | P1 | ANTI_JITTER_METHODS |
| LL-012 | Linux : doc ALSA direct / JACK faible latence (option avancée) | P2 | LINUX_AUDIO_OPTIONS |
| LL-013 | Windows : éviter MME par défaut si WASAPI disponible ; message si fallback MME | P1 | P1-P9 preferred hosts |
| LL-014 | macOS : Core Audio ; note limitations PortAudio documentées | P1 | OPTIONS_JITTER_5MS |
| LL-015 | Option `iti_jitter_s` entre essais (uniforme) pour protocoles type P1-P9 | P2 | manip JSON |
| LL-016 | Import bloc `audio` depuis `manip_psychophysique_json` existant | P2 | P1-P9 |
| LL-017 | Pygame mixer : buffer minimal (64) si audio pygame + warning si mix avec low_latency | P2 | ANTI_JITTER_METHODS |
| LL-018 | Métriques export : `av_offset_measured_ms`, jitter std par session | P2 | compare_audio_methods |
| LL-019 | Profil pip **`requirements-lowlatency.txt`** : sounddevice, soundfile, numpy | P0 | séparé de psychopy |
| LL-020 | **Ne pas** imposer PsychoPy pour l’audio low-latency — PortAudio utilisable avec affichage pygame ou psychopy | P0 | séparation couches |

### 5.4 Questionnaires et réponses comportementales

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-301 | Nœud `questionnaire` : N questions dynamiques (pas seulement 7) | P0 | Arôme |
| F-302 | Types de réponse : échelle Likert (slider), choix unique, choix multiple, texte court | P1 | Arôme (slider) |
| F-303 | Option « Je ne sais pas » par question | P0 | Arôme |
| F-304 | Timeout configurable (défaut 60 s) + passage auto | P0 | Arôme |
| F-305 | Bouton valider explicite en plus du timeout | P1 | — |
| F-306 | Nœud `keyboard_response` : une touche / deux touches (ex. B vs M) | P1 | randomflow |
| F-307 | Nœud `keyboard_rating` : jugement continu ou discret (trop tôt / trop tard) | P2 | occultation |
| F-308 | Enregistrement temps de réponse (ms depuis début nœud) | P1 | randomflow |
| F-309 | Consignes affichées au-dessus du stimulus ou en écran dédié | P1 | — |

### 5.5 Stimuli moteur Pygame (générés, non fichier)

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-401 | Moteur **pygame** enregistré ; fenêtre plein écran dédiée par défaut | P0 | randomflow, shadowi, MOT |
| F-401b | (P2) Surface Pygame embarquée dans fenêtre Qt | P2 | — |
| F-402 | Nœud `optic_flow` : paramètres JSON (cohérence, nb points, mode brownian/reverse, touches) | P2 | randomflow |
| F-403 | Nœud `mot` : tracking balles (paramètres vitesse, nb cibles, masque) | P3 | MOT |
| F-404 | Nœud `shadow_ball` : scène balle/ombre simplifiée (preset conditions) | P3 | shadowi |
| F-405 | Nœud `occultation` : balle + occulteur, options cercle 0/1/2 | P3 | occultation |
| F-406 | Nœud `occultation_ttc` : trajectoires depuis matrice JSON | P3 | occultation Action |
| F-407 | Warmup frames avant affichage (flux optique) | P3 | randomflow |

### 5.5b Stimuli moteur PsychoPy

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-451 | Moteur **psychopy** enregistré ; fenêtre et horloge par session ou par nœud | P1 | audi_visuel |
| F-452 | Liste et sélection du périphérique audio (prefs PsychoPy / config) | P1 | `main_psychopy.py` |
| F-453 | Carré photosonde (coin écran) + log timestamp | P2 | P1-P9, audi_visuel |
| F-454 | Pré-allocation buffers affichage PsychoPy ; audio critique délégué à **LL-*** si `low_latency` | P2 | anti-jitter P1-P9 |
| F-455 | Import essais `manip_psychophysique_json` (conditions, timing, audio section) | P2 | P1-P9 |
| F-456 | Nœud occultation Action (`occ_action_psychopy`) en preset psychopy | P3 | occultation |

### 5.6 Triggers et I/O matériel

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-501 | Nœud `trigger` série : port, baud, valeur(s), délai | P0 | Arôme |
| F-502 | Profils de trigger nommés (`cedrus`, `arduino_ttl`, custom) | P1 | P1-P9, Arduino |
| F-503 | Nœud `wait_key` : touche(s) attendue(s), message | P0 | Arôme + triggerAnaelle |
| F-504 | Simulation trigger clavier HID (debug sans Arduino) | P1 | triggerAnaelle |
| F-505 | Nœud `delay` : attente pure (ms) | P0 | — |
| F-506 | Export triggers vers **LSL** (marqueurs stream) | P2 | P1-P9_LSL |
| F-507 | Sync **TR IRM** (lecture trigger scanner, timestamp TR) | P3 | P1-P9.py |
| F-508 | Photosonde : carré blanc coin écran + timestamp log (tous moteurs + low_latency) | P1 | audi_visuel, P1-P9 |
| F-509 | Joy-Con / USB Cedrus comme entrée réponse | P3 | P1-P9 tests |

### 5.7 Oculométrie (EyeLink)

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-601 | Mode EyeLink optionnel : connexion, calib HV5, EDF par sujet | P3 | shadowi, MOT |
| F-602 | Messages EyeLink par nœud (START/STOP trial, condition ID) | P3 | shadowi |
| F-603 | Mode dummy EyeLink (sans matériel) | P3 | shadowi DEVELOPER_GUIDE |
| F-604 | Export métadonnées essai vers CSV session (lien fichier EDF) | P3 | — |

### 5.8 Logging et export données

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-701 | Fichier session unique : `sessions/<subject>_<timestamp>.csv` | P0 | Arôme |
| F-702 | Colonnes normalisées : `timestamp_iso`, `timestamp_ms`, `subject_id`, `node_index`, `node_type`, `node_id`, `stimulus`, `response`, `rt_ms` | P0 | — |
| F-703 | Export JSON miroir (`responses.json` style randomflow) | P1 | randomflow |
| F-704 | Copie du protocole exécuté dans dossier session (reproductibilité) | P1 | — |
| F-705 | Log événements techniques (erreurs média, latence chargement) | P2 | P1-P9 doc_dev |
| F-706 | Horodatage `perf_counter` dans tous les logs low_latency | P0 | P1-P9 |
| F-707 | Export colonnes sync dérivées (`video_first_flip - audio_actual`) par essai | P1 | manip JSON log |

### 5.9 Éditeur / création de manip simplifiée (Concepteur)

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-801 | UI liste des nœuds (ajouter, supprimer, dupliquer, réordonner drag-and-drop) | P1 | Objectif produit |
| F-802 | Formulaire par type de nœud (pas d’édition JSON brute obligatoire) | P1 | — |
| F-803 | Bibliothèque médias : scan dossier `video/`, `audio/`, aperçu | P1 | Arôme |
| F-804 | Templates protocole : « Vidéo + QCM », « A/V looming », « Optic flow B/M » | P2 | Inventaire travaux |
| F-805 | Validation JSON (schéma, fichiers manquants) avant run | P1 | — |
| F-806 | Aperçu participant (fenêtre réduite, un nœud) | P2 | — |
| F-807 | Import depuis protocoles existants (`experiment1-9.json`, randomflow `config.json`) | P2 | Arôme, randomflow |
| F-808 | Export package : `protocol.json` + `assets/` zip pour transfert poste | P2 | — |

### 5.10 Configuration application et déploiement

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-901 | Fichier `settings.json` : dossier données, ports série par défaut, plein écran | P1 | Pattern `config.json` labo |
| F-902 | Vérification dépendances au lancement (`check_dependencies`) | P1 | audi_visuel |
| F-903 | Installateur / script setup (**uv**, profils par extra) | P0 | `uv sync --extra qt` |
| F-904 | Profils : `qt`, `pygame`, `psychopy`, `lowlatency` (`pyproject.toml` + `uv.lock`) | P0 | 2 env uv si conflit pygame↔psychopy |
| F-904b | Fichiers : `requirements-qt.txt`, `-pygame.txt`, `-psychopy.txt`, **`-lowlatency.txt`**, `-full.txt` | P1 | lowlatency = sounddevice+soundfile |
| F-904c | Doc installation **WASAPI** : casque/sortie exclusive, éviter Bluetooth pour essais sync | P1 | expérience terrain Windows |
| F-905 | Documentation utilisateur intégrée (aide F1) + `doc_user.md` | P1 | P1-P9 |
| F-906 | Mode kiosque : empêcher fermeture accidentelle, masquer barre menu | P1 | — |
| F-907 | Support Windows + macOS (chemins, COM vs `/dev/cu.*`) | P0 | P1-P9, Arôme |
| F-908 | Support **Linux** poste labo (ALSA, chemins `/dev/ttyUSB*`) | P1 | linux/ P1-P9 |
| F-909 | `environment.json` auto à chaque session (versions, OS, GPU) | P1 | Reproductibilité O8 |

### 5.11 Design expérimental et randomisation

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-1101 | Section `conditions[]` + expansion en essais avec `repetitions` | P2 | manip_psychophysique_json |
| F-1102 | `randomize_trials` + `random_seed` pour séquences reproductibles | P2 | P1-P9 |
| F-1103 | `iti_jitter_s` entre essais (uniforme) | P2 | P1-P9 |
| F-1104 | Nœud `block_break` : pause consigne + attente touche expérimentateur | P2 | — |
| F-1105 | Counterbalancing Latin square (grille dans JSON) | P3 | — |
| F-1106 | Exclusion de conditions par `group` sujet (`subject.group`) | P2 | — |
| F-1107 | Liste `allowed_keys` globale + `quit_key` (comme P1-P9) | P1 | manip JSON |
| F-1108 | `response_window_s` + `mandatory` + timeout logique | P2 | P1-P9 |

### 5.12 Affichage et contrôle écran

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-1201 | `display.fullscreen`, `display.screen_index` dans protocole | P1 | P1-P9 |
| F-1202 | Positionnement pygame sur écran externe (`SDL_VIDEO_WINDOW_POS`) | P2 | MOT_Tunnel |
| F-1203 | Détection nombre d’écrans + avertissement si `screen_index` invalide | P1 | — |
| F-1204 | Mode fenêtré debug (bordure, 1280×720) pour Concepteur | P1 | — |
| F-1205 | Fond noir inter-nœud (handoff moteurs, anti flash) | P1 | E-004 |
| F-1206 | Carré photosonde paramétrable (taille, position, durée flash) | P1 | P1-P9 |
| F-1207 | Mesure / log refresh rate écran au démarrage session | P2 | — |
| F-1208 | Calibration luminosité : consigne « régler luminance externe » (pas de cal hardware v1) | P3 | — |

### 5.13 Médias, formats et assets

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-1301 | Vidéo : **MP4** (H.264) recommandé ; liste codecs supportés par moteur | P1 | Arôme, MoviePy |
| F-1302 | Audio essais critiques : **WAV** PCM (16/24 bit) ; conversion avertissement si MP3 | P1 | P1-P9 |
| F-1303 | Chemins relatifs au dossier protocole ; interdiction `..` (path traversal) | P0 | NF sécurité |
| F-1304 | Hash SHA-256 des médias référencés dans `protocol.hash` | P2 | O8 |
| F-1305 | Validation durée média vs `stimulus_duration_s` (avertissement si tronqué) | P2 | manip JSON |
| F-1306 | Images PNG/JPG pour `image` et fixation | P1 | — |
| F-1307 | Taille max fichier configurable (avertissement > 500 Mo) | P2 | — |
| F-1308 | Nommage assets : convention `videos/`, `audio/`, `images/` | P1 | Arôme |

### 5.14 Fiabilité, reprise et modes d’exécution

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-1401 | **Dry-run** : valider protocole + médias + deps sans fenêtre participant | P1 | — |
| F-1402 | **Run practice** : flag session, données séparées ou suffixe `_practice` | P2 | F-008 |
| F-1403 | Crash mid-session : écriture `events.jsonl` flush ; fichier `.crash` avec dernier nœud | P1 | — |
| F-1404 | Reprise manuelle : redémarrer à `node_index` (expérimentateur, pas participant) | P3 | — |
| F-1405 | Confirmation avant quit (`quit_key` + dialogue) | P1 | P1-P9 |
| F-1406 | Verrouillage protocole « approuvé » (`locked: true` → lecture seule en run) | P3 | Pré-enregistrement |
| F-1407 | Double confirmation lancement sur poste non calibré (audio check échoué) | P2 | — |

### 5.15 Sécurité, confidentialité et éthique

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-1501 | Pas d’`eval` / pas de code Python **en string** dans le JSON — uniquement fichiers `scripts/*.py` (PY-018) | P0 | NF-05 |
| F-1508 | Bannière « protocole avec code personnalisé » avant run si `python_task` présent | P1 | confiance |
| F-1509 | Liste des scripts chargés + hash SHA-256 dans `environment.json` | P2 | reproductibilité |
| F-1502 | `subject_id` pseudonyme ; pas de champ nom/prénom par défaut | P1 | RGPD recherche |
| F-1503 | Dossier sessions hors cloud ; droits OS recommandés (chmod doc) | P1 | — |
| F-1504 | Nœud optionnel `consent` (texte + attente touche) | P2 | — |
| F-1505 | Nœud `debrief` (écran fin, markdown) | P2 | — |
| F-1506 | Champ optionnel `ethics_protocol_id` dans métadonnées protocole | P2 | — |
| F-1507 | Journal audit : qui a lancé (`experimenter`), quand, quel hash protocole | P1 | O8 |

### 5.16 Extensions, plugins et API interne

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-1601 | Registre `pygame_handlers` : `{ "optic_flow": handler }` — alternative **déclarative** à `python_task` pour scènes réutilisables | P2 | E-007 ; voir §4.10 |
| F-1602 | Hooks orchestrateur : `on_node_start`, `on_node_end`, `on_session_end` | P3 | LSL, custom |
| F-1603 | Fichier `the_kit.toml` local : chemins data, devices par défaut | P2 | settings |
| F-1604 | Variables protocole `{{subject_id}}` dans chemins / consignes | P2 | — |
| F-1605 | Export **sidecar BIDS-like** minimal (`participants.tsv`, `events.tsv`) | P3 | Neuroimaging |
| F-1606 | API Python `from the_kit import run_protocol` pour scripts labo | P2 | — |

### 5.18 Tâches Python (fichier `.py`, inline)

> Spécification complète : **§4.10**. Package API : `the_kit.task_api`.

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| PY-001 | Nœud **`python_task`** référencé dans `nodes[]` comme tout autre type | P1 | OpenSesame inline_script |
| PY-002 | Chargement module depuis `{protocol}/scripts/` uniquement ; rejet `..` et chemins absolus | P0 | Sécurité |
| PY-003 | Phases **`prepare`** et **`run`** (run obligatoire, prepare optionnel) | P1 | OpenSesame |
| PY-004 | Objet **`TaskContext`** documenté (`the_kit/task_api.py`) | P1 | §4.10 |
| PY-005 | **`ctx.variables`** persistant session ; export dans `events.jsonl` / CSV | P1 | var.* OS |
| PY-006 | **`ctx.log.event`**, **`ctx.trigger.serial`**, accès **`ctx.audio`** / **`ctx.display`** | P1 | intégration |
| PY-007 | Retour structuré `NodeResult` (status, data, responses, rt_ms) | P1 | orchestrateur |
| PY-008 | `timeout_s` par nœud ; interruption propre → status `error` | P1 | — |
| PY-009 | `on_error`: `abort` \| `skip` \| `retry_once` | P1 | — |
| PY-010 | Éditeur : ajouter nœud « Tâche Python », picker fichier `scripts/*.py`, choix fonctions | P2 | O12 |
| PY-011 | Template `scripts/_template_task.py` à la création protocole | P2 | — |
| PY-012 | `the_kit validate` : imports résolvables, fonctions `run`/`prepare` existantes | P1 | — |
| PY-013 | Dry-run : exécuter `prepare` sans fenêtre participant | P1 | F-1401 |
| PY-014 | Support `scripts/utils.py` importé par tâches du même dossier | P1 | — |
| PY-015 | Exemple dans repo : `examples/protocol_with_python/` | P1 | doc |
| PY-016 | **`engine: python`** enregistré dans `check-engines` | P1 | E-002 |
| PY-017 | Traceback loggé dans `the_kit.log` + événement `python_error` | P0 | debug labo |
| PY-018 | Interdiction code Python embarqué en string dans JSON (→ utiliser `file`) | P0 | F-1501 |
| PY-019 | (P2) Accès **`ctx.get_engine("psychopy")`** pour dessiner dans `run` | P2 | glue visuel |
| PY-020 | (P3) Sandbox RestrictedPython ou liste blanche imports | P3 | durcissement |

### 5.17 Qualité, tests et observabilité

| ID | Fonctionnalité | Priorité | Source |
|----|----------------|----------|--------|
| F-1701 | Tests unitaires : parse protocole, adaptateur Arôme v0 | P0 | Phase 0 |
| F-1702 | Tests intégration : session mock sans matériel (dummy audio/video) | P1 | — |
| F-1703 | Test non-régression low_latency : compare timestamps ref P1-P9 (tolérance ms) | P1 | LL-018 |
| F-1704 | CI locale / GitHub Actions : lint + tests sur `qt-only` profile | P2 | — |
| F-1705 | Niveaux log `DEBUG/INFO/WARNING` ; `--verbose` CLI | P1 | — |
| F-1706 | Métriques post-session : durée totale, nb nœuds, erreurs, jitter moyen | P1 | — |
| F-1707 | Rapport HTML session (option) pour expérimentateur | P3 | — |

---

## 6. Schéma de protocole cible (évolution JSON)

### 6.1 Enveloppe

```json
{
  "protocol_version": "1.0",
  "name": "Arome_respiration_2026",
  "loop": 1,
  "randomize_blocks": false,
  "subject": { "id": "S001", "group": "odor_A" },
  "audio_defaults": {
    "timing_mode": "low_latency",
    "blocksize": 128,
    "scheduling_lead_s": 0.3,
    "offset_ms": 0
  },
  "nodes": []
}
```

### 6.2 Exemple de nœud avec moteur et low-latency

```json
{
  "id": "trial_flow_01",
  "type": "optic_flow",
  "engine": "pygame",
  "params": { "dot_coherence": 0.8, "noise_mode": "brownian" }
}
```

```json
{
  "id": "loom_trial",
  "type": "av_sync",
  "engine": "psychopy",
  "timing_mode": "low_latency",
  "params": {
    "video": "videos/forward.mp4",
    "audio": "audio/Looming1000-30-90exp500ms.wav",
    "offset_ms": -12,
    "stimulus_duration_s": 2.0
  },
  "audio": {
    "audio_device_query": "speakers",
    "blocksize": 128,
    "output_sample_rate": 44100
  }
}
```

### 6.3 Types de nœuds planifiés

| Type | Famille visuelle §4.9 | Moteur défaut | `timing_mode` | Description |
|------|----------------------|---------------|---------------|-------------|
| `video` | **A** fichier | qt | standard | Vidéo MP4 + `duration_s` |
| `image` | **A** fichier | qt | standard | Image statique |
| `slideshow` | **A** fichier | qt | standard | Liste images |
| `av_sync` | **A** fichier + audio | psychopy | **low_latency** | Vidéo fichier + WAV sync |
| `shapes` | **B** généré | psychopy | standard | Formes primitives |
| `fixation` | **B/C** généré | psychopy | standard | Croix / point (alias shapes) |
| `optic_flow` | **B** généré | pygame | standard | Flux optique points |
| `mot` | **B** généré | pygame | standard | Multiple object tracking |
| `shadow_ball` | **B** généré | pygame | standard | Balle + ombre 3D |
| `occultation` | **B** généré | pygame | standard | Occultation classique |
| `occultation_ttc` | **B** généré | psychopy | standard | Time-to-contact |
| `psychopy_stim` | **B** généré | psychopy | standard | Text, grating, etc. |
| `pygame_scene` | **B** généré | pygame | standard | Handler custom |
| `blank` | **C** overlay | qt | standard | Écran uni (ITI) |
| `photosonde_square` | **C** overlay | psychopy | standard | Flash calibration |
| `instructions` | **C** UI | qt | standard | Consignes texte |
| `questionnaire` | **C** UI | qt | standard | QCM (ex-Arôme) |
| `keyboard_response` | **D** composite | pygame | standard | Réponse pendant/après visuel |
| `audio` | — (auditif) | psychopy | **low_latency** | Son seul |
| `wait_key` | — | qt | standard | Gate manuel |
| `trigger` | — | — | — | Sortie série |
| `delay` | — | — | — | Pause |
| `psychopy_routine` | **B** généré | psychopy | low_latency si audio | Routine paramétrée |
| **`python_task`** | **E** inline code | **python** | — | Fichier `scripts/*.py` prepare/run |

### 6.3b Exemple enchaînement avec tâche Python

```json
{
  "nodes": [
    { "type": "instructions", "engine": "qt", "text": "Bienvenue" },
    {
      "type": "python_task",
      "engine": "python",
      "script": { "file": "scripts/setup_hardware.py", "run": "run", "prepare": "prepare" }
    },
    { "type": "av_sync", "engine": "psychopy", "timing_mode": "low_latency", "params": { "video": "videos/forward.mp4", "audio": "audio/loom.wav" } },
    {
      "type": "python_task",
      "engine": "python",
      "script": { "file": "scripts/log_trial.py", "run": "run", "args": { "condition": "loom" } }
    },
    { "type": "questionnaire", "engine": "qt", "questions": [] }
  ]
}
```

### 6.3c Schéma commun champ `visual` (stimuli générés)

```json
{
  "type": "shapes",
  "engine": "pygame",
  "duration_s": 2.0,
  "visual": {
    "background": [0, 0, 0],
    "elements": [
      { "shape": "circle", "radius_px": 40, "position": [960, 540], "color": [255, 0, 0], "fill": true }
    ]
  }
}
```

Pour les scènes labo (`optic_flow`, `mot`, …), `visual` est remplacé ou complété par **`params`** spécifiques au preset (voir docs randomflow / shadowi).

**Compatibilité Arôme v0** : import sans `engine` → `engine: "qt"`, `timing_mode: "standard"` ; ajout de `protocol_version`.

### 6.4 Validation JSON Schema

| ID | Exigence | Priorité |
|----|----------|----------|
| S-001 | Fichier `schemas/protocol-v1.schema.json` (JSON Schema Draft 2020-12) | P1 |
| S-002 | `the_kit validate protocol.json` — erreurs lisibles (ligne, champ) | P1 |
| S-003 | Schémas par type de nœud (`nodes/definitions/video.json`, …) | P2 |
| S-004 | Versioning schéma lié à `protocol_version` | P1 |

### 6.5 Événements `events.jsonl` (format unifié)

Chaque ligne = un objet JSON (append-only) :

| Champ | Description |
|-------|-------------|
| `ts_perf` | `time.perf_counter()` |
| `ts_iso` | ISO 8601 locale |
| `event` | `node_start`, `node_end`, `response`, `trigger`, `audio_actual_start`, `video_first_flip`, `error`, … |
| `node_id`, `node_type`, `engine`, `timing_mode` | Contexte |
| `payload` | Objet libre (réponse, RT, valeur trigger, offset ms, …) |

Avantage : recovery crash, import analyse, compat LSL ultérieur.

### 6.6 Matrice présentation visuelle par moteur

| Capacité visuelle | Qt | Pygame | PsychoPy |
|-------------------|-----|--------|----------|
| Vidéo fichier (MP4) | ✅ QMediaPlayer | ⚠️ OpenCV / bridge | ✅ MoviePy frames |
| Image fichier | ✅ | ✅ | ✅ |
| Diaporama | ✅ (P2) | ✅ | ✅ |
| Formes primitives | ⚠️ limité | ✅ | ✅ |
| Flux optique / MOT | ❌ | ✅ | ⚠️ |
| Scène 3D ombre / occultation | ❌ | ✅ | ⚠️ TTC |
| Grating / texte psycho | ❌ | ⚠️ | ✅ |
| Overlay photosonde | ⚠️ | ✅ | ✅ |
| Questionnaire / instructions | ✅ | ❌ | ⚠️ |

### 6.7 Matrice formats fichier (assets)

| Format | Qt | Pygame | PsychoPy | Low-latency audio |
|--------|-----|--------|----------|-------------------|
| MP4 (H.264) | ✅ | ⚠️ OpenCV | ✅ MoviePy | — |
| WAV PCM | — | — | — | ✅ essais sync |
| MP3 | ✅ (vidéo) | ⚠️ | ✅ | ❌ sync critique |
| PNG/JPG | ✅ | ✅ | ✅ | — |

---

## 7. Exigences non fonctionnelles

| ID | Exigence | Cible |
|----|----------|-------|
| NF-01 | Latence démarrage vidéo suivante | < 500 ms après préchargement (P1) |
| NF-02 | Stabilité session | Pas de crash silencieux ; log + dialogue |
| NF-03 | Reproductibilité | Hash protocole + version app dans chaque session |
| NF-04 | Accessibilité participant | Texte lisible, contraste, pas de souris requise en run |
| NF-05 | Sécurité | Pas d’exécution de code arbitraire depuis JSON |
| NF-06 | Performance optic flow | ≥ 60 FPS sur GPU labo standard (P2) |
| NF-07 | Licence | Dépendances compatibles usage académique |
| NF-08 | Isolation moteurs | PsychoPy et Pygame peuvent coexister via venv/proc séparé si conflit binaire |
| NF-09 | Parité OS | macOS + Windows + Linux ; par moteur et par host API audio |
| NF-10 | Audio low-latency | Avec `timing_mode: low_latency`, pas de mixer pygame/Qt pour la piste critique |
| NF-11 | Jitter labo (indicatif) | Objectif **&lt; 10 ms** matériel A/V sur poste calibré ; log obligatoire si hors seuil |
| NF-12 | Blocksize | Valeur par défaut conservative (128) ; 64 sur machine dédiée documentée |
| NF-13 | Bluetooth | Avertissement si sortie BT détectée pour essais sync |
| NF-14 | Référence code P1-P9 | Module low-latency traçable vers `manip_psychophysique_json` (tests de non-régression) |
| NF-15 | Disponibilité | Run participant ≥ 2 h sans fuite mémoire grossière (sessions longues Arôme) |
| NF-16 | Récupération | Après crash, ≥ 90 % des événements récupérables via `events.jsonl` |
| NF-17 | Confidentialité | Pas de télémétrie cloud par défaut ; opt-in explicite si un jour ajouté |
| NF-18 | Maintenabilité | Couverture tests unitaires ≥ 60 % sur `protocol/` et `audio/low_latency` (P2) |
| NF-19 | Accessibilité expérimentateur | UI Concepteur : contrastes WCAG AA (P2) ; participant : gros texte configurable |
| NF-20 | Localisation | Chaînes UI en français v1 ; architecture prête EN (fichiers `.ts` ou JSON i18n P3) |
| NF-21 | CPU | Option `cpu_affinity` documentée (P3) ; pas activée par défaut |
| NF-22 | Disque | Session typique &lt; 50 Mo sans copie médias ; avec copie assets selon config |

---

## 8. Roadmap proposée

### Phase 0 — Fondation orchestrateur (P0) ✅ *livrée 2026-05-22 — v0.1.0a0*

- Package `the_kit` : orchestrateur + **Engine Qt** (port `psychophysique_app.py`)
- Adaptateur protocole Arôme v0 → `engine: qt` (`protocol/loader.py`)
- CLI : `run`, `validate`, `check-engines`, `--dry-run` ; session `events.jsonl` + `responses.csv`
- `schemas/protocol-v1.schema.json` ; tests pytest ; [doc_user.md](./doc_user.md)
- Détail jalons : [ROADMAP.md](./ROADMAP.md) §3

**Reste validation terrain** : run manuel `experiment9_notrig.json` avec assets `video/` (régression Arôme).

### Phase 1 — Trois moteurs + low-latency + Python inline (P1) ✅ *livrée 2026-05-22 — v0.2.0a0*

- **Couche LL** : `audio/low_latency.py`, `check-audio` CLI
- **Pygame** : `optic_flow`, `keyboard_response`
- **PsychoPy** : `av_sync`, `fixation`, `audio` (install : `uv pip install psychopy==2023.2.3 moviepy`)
- **Python** : `python_task`, `task_api.py` ; démo `examples/demo_multi_engine/`
- Orchestrateur multi-moteur + `display/manager.py` handoff
- Détail : [ROADMAP.md](./ROADMAP.md) §4

### Phase 2 — Labo multimodal (P2) ✅ *livrée 2026-05-22 — v0.3.0a0*

- `conditions[]` → expansion essais (`protocol/expander.py`)
- `import-p19`, `export-zip`, `environment.json` + hash médias
- Concepteur `the_kit design` ; presets `examples/presets/`
- Nœuds `consent`, `debrief`, `slideshow`, `block_break`, `photosonde_square`
- Détail : [ROADMAP.md](./ROADMAP.md) §5

### Phase 3 — Intégrations avancées (P3) ✅ `0.4.0a0`

- Livré : `shadow_ball`, `occultation`, `mot` (pygame) ; `occultation_ttc`, `psychopy_stim` (psychopy) ; LSL (`lsl` section + `check-lsl`) ; EyeLink wrapper + `eyelink_calib.py` (dummy)
- Hors scope v1 : TR IRM intégré ; embed Pygame dans Qt
- Terrain : calibration oscilloscope — [doc_calibration.md](./doc_calibration.md)

### Phase 4 — Maturité (M4) ✅ `0.5.0a0`

- Export BIDS-like (`export-session`, `bids/*_events.tsv`)
- Rapport HTML `session_report.html`
- Latin square dans `presentation.counterbalance`
- CI GitHub Actions ; `scripts/run_the_kit.command`

---

## 9. Mapping inventaire Travaux → fonctionnalités

| Outil d’origine | Apport principal au PRD |
|---------------|-------------------------|
| **Projet Arôme** | **Exemple Qt** — vidéo, QCM, trigger, wait_key, JSON |
| **P1-P9 / manip_psychophysique_json** | **Low-latency** : sounddevice, WASAPI, callbacks, `perf_counter`, anti-jitter, logs sync ; PsychoPy affichage |
| **audi_visuel** | **Pygame + PsychoPy + PortAudio** — 2 venv, photosonde, offset A/V |
| **randomflow** | **Pygame** — flux optique, réponses B/M |
| **shadowi** | **Pygame** — scène 3D, EyeLink |
| **occultation** | **Pygame + PsychoPy** — TTC ; HTML hors moteurs |
| **MOT / MOT_Tunnel** | MOT, scotome, second écran |
| **opticflow_Alba** | Lecture vidéo simple OpenCV |
| **Arduino triggerAnaelle** | TTL → touche T |
| **NiDaq Digitimer** | Non intégré — stimulation entrante distincte |
| **alba_eyetracker_data** | Post-traitement — export compatible ASC/CSV |
| **NIRS_Test** (P1-P9) | Harness stimulation fNIRS — preset trigger P3 |
| **pipe_data_HRV** | Hors The Kit — export timestamps compatible |

---

## 10. Critères d’acceptation v1 (MVP)

1. Protocole démo : nœuds **qt + pygame + psychopy**, dont un `av_sync` avec **`timing_mode: low_latency`**.
2. Import Arôme : `experiment9.json` en `engine: qt`, `timing_mode: standard`.
3. Logs : `engine`, `timing_mode`, `audio_hostapi` (ex. `Windows WASAPI`), timestamps `*_perf` sur essai low-latency.
4. `the_kit check-engines` et **`the_kit check-audio`** (host APIs, devices, blocksize conseillé).
5. Profils pip dont **`requirements-lowlatency.txt`** ; doc WASAPI Windows.
6. Non-régression : essai type P1-P9 (forward + WAV) avec jitter loggé &lt; seuil documenté sur poste référence.
7. `the_kit validate` et `dry-run` passent sur protocole démo avant tout run participant.
8. Crash simulé : `events.jsonl` contient les nœuds terminés avant arrêt.
9. Protocole avec `python_task` : `scripts/hello.py` exécuté entre deux nœuds Qt ; `ctx.variables` exporté dans les logs.

---

## 11. Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| Conflits deps PyQt6 / Pygame / PsychoPy | Trois fichiers requirements + venv séparés ; subprocess PsychoPy (P2) |
| Handoff fenêtre / focus entre moteurs | Séquence fermeture/ouverture documentée ; écran noir inter-nœud optionnel |
| Précision A/V insuffisante en Qt | `timing_mode: low_latency` + PortAudio ; affichage psychopy/pygame |
| WASAPI indisponible / fallback MME | Avertissement + jitter attendu plus élevé ; doc changement périphérique |
| PortAudio macOS capricieux | Documenter Core Audio ; tests `check-audio` ; venv dédié |
| Complexité éditeur | MVP : formulaires + JSON avancé en onglet expert |
| EyeLink / LSL fragiles par OS | Modules optionnels, tests dummy, doc par plateforme |
| Perte données participant | `events.jsonl` append-only ; copie protocole en session |
| Protocole JSON invalide | JSON Schema + validate avant run |
| Médias manquants sur autre poste | Export zip F-808 ; chemins relatifs |
| RGPD / données personnelles | Pseudonymisation par défaut ; doc éthique F-150* |
| Code Python malveillant dans `scripts/` | Confiance labo ; hash scripts dans session ; doc responsabilité PI |

---

## 12. Fichiers et dépôts

| Élément | Chemin / remote |
|---------|-----------------|
| The Kit (ce PRD + code futur) | `~/Documents/TheKit/the_kit` |
| Exemple Qt (v0) | `~/Documents/Projet_Arome_ANAELLE` |
| Réf. Pygame | randomflow, shadowi, MOT, occultation |
| Réf. PsychoPy | `audi_visuel`, P1-P9 (affichage) |
| Réf. Low-latency | P1-P9 `manip_psychophysique_json/main.py`, `ANTI_JITTER_METHODS.md`, `LINUX_AUDIO_OPTIONS.md`, `OPTIONS_JITTER_5MS.md` |
| Référence sync A/V | `ROSITO/audi_visuel`, `ROSITO/P1-P9` |
| Vault doc | `obsidian_vault/Travaux/Projets/Projet_Arome_ANAELLE.md` |
| Mémoire projet | `./MEMORY.md` |
| Architecture | `./ARCHITECTURE.md` |

---

## 13. Matrice matériel et pilotes

| Matériel / logiciel | Support v1 | Interface | Note |
|---------------------|------------|-----------|------|
| Écran participant dédié | P1 | `screen_index`, SDL pos | MOT_Tunnel |
| Casque filaire analogique/USB | P1 | WASAPI / Core Audio | Éviter BT pour sync |
| Arduino Micro (HID **T**) | P1 | `wait_key` | triggerAnaelle |
| Port série TTL (Arôme) | P0 | `trigger` pyserial | COM / `/dev/cu.*` |
| Cedrus response box | P3 | USB / pyxid | P1-P9 tests |
| EyeLink 1000+ | P3 | pylink | shadowi, MOT |
| Photosonde + oscilloscope | P1 | carré écran + log | calibration ms |
| Scanner IRM (TR) | P3 | pipeline P1-P9.py | hors orchestrateur v1 |
| LSL réseau local | P2–P3 | pylsl | marqueurs |
| GPU intégré / dédié | P1 | doc pilotes | PsychoPy fullscreen |

---

## 14. Positionnement vs outils existants

| Outil | Rapport à The Kit |
|-------|-------------------|
| **PsychoPy Builder** | The Kit ne remplace pas l’éditeur visuel ; peut exécuter des routines paramétrées |
| **OpenSesame** | Même niche ; The Kit reprend **`inline_script`** via **`python_task`** + fichiers `scripts/` |
| **Arôme seul** | Sous-ensemble Qt ; The Kit l’importe |
| **P1-P9 scripts** | Référence low-latency ; The Kit porte et unifie |
| **Expyriment / Pavlovia** | Pas de déploiement web v1 ; offline local |
| **Presentation** | Legacy ; The Kit cible Python moderne |

**Différenciation** : un seul install labo, trois moteurs + WASAPI, héritage direct des manips CerCo déjà validées.

---

## 15. Qualité, tests et versionnement

### 15.1 Stratégie de test

| Couche | Outils | Cible |
|--------|--------|-------|
| Unit | `pytest` | parse JSON, adaptateur Arôme, choix device mock |
| Intégration | pytest + fixtures médias | session dry-run, CSV/events |
| Hardware-in-loop | manuel | `check-audio`, photosonde, poste Windows WASAPI |
| Non-régression | script compare logs P1-P9 | low_latency timestamps |

### 15.2 Versionnement produit

| Élément | Format | Exemple |
|---------|--------|---------|
| Application | SemVer | `the_kit 0.1.0` |
| Protocole | `protocol_version` dans JSON | `"1.0"` |
| Schéma | lié au protocol_version | `protocol-v1.schema.json` |
| Session | horodatage dossier | `20260522_S012_143022` |

### 15.3 Migration protocoles

| De → Vers | Comportement |
|-----------|--------------|
| Arôme v0 → v1 | Import auto `engine: qt`, ajout champs défaut |
| v1.0 → v1.1 (futur) | Script `the_kit migrate` + changelog |

### 15.4 Documentation livrable

| Doc | Public | Phase |
|-----|--------|-------|
| `doc_user.md` | Expérimentateur | 1 |
| `doc_technician.md` | WASAPI, photosonde, check-audio | 1 |
| `doc_dev.md` | Moteurs, plugins | 2 |
| `CHOIX_MOTEUR.md` | Quand Qt / pygame / psychopy | 1 |

---

## 16. Glossaire

| Terme | Définition |
|-------|------------|
| **Moteur (engine)** | Backend d’affichage / UI : `qt`, `pygame` ou `psychopy` |
| **timing_mode** | `standard` ou `low_latency` (couche PortAudio / WASAPI / Core Audio / ALSA) |
| **Host API** | Interface bas niveau PortAudio : ex. **Windows WASAPI**, Core Audio, ALSA |
| **PortAudio** | Couche native utilisée par **sounddevice** pour audio callback |
| **Orchestrateur** | Cœur The Kit : enchaîne les nœuds, moteurs et mode timing |
| **Nœud** | Étape atomique du protocole (vidéo, QCM, etc.) |
| **Protocole** | Fichier JSON décrivant l’enchaînement des nœuds |
| **Arôme** | Projet historique servant de **référence Qt**, pas le nom du produit |
| **Session** | Une exécution complète pour un sujet donné |
| **Trigger** | Signal sortant (série, LSL) ou attendu (touche) |
| **Photosonde** | Détection flash écran pour calibration temporelle |
| **Stimulus visuel** | Tout contenu affiché à l’écran pour le participant (fichier, généré ou overlay) |
| **Famille A/B/C** | Classification §4.9 : fichier / généré / overlay UI |
| **`shapes`** | Nœud formes primitives (cercle, croix, grille, …) |
| **`visual`** | Bloc JSON décrivant fond + éléments graphiques générés |
| **`python_task`** | Nœud exécutant un fichier `scripts/*.py` (type OpenSesame inline_script) |
| **`TaskContext` (`ctx`)** | API injectée dans prepare/run : session, variables, log, devices |
| **`ctx.variables`** | Magasin persistant clé/valeur pendant la session |
| **ITI** | Inter-trial interval — délai entre deux essais |
| **Trial / essai** | Une présentation stimulus + collecte réponse |
| **Condition** | Cellule factorielle (stimulus A vs B, etc.) |
| **Dry-run** | Validation sans participant réel |
| **events.jsonl** | Journal append-only ligne par ligne |
| **WASAPI** | Windows Audio Session API — host API PortAudio prioritaire sous Windows |
| **JSON Schema** | Validation structurelle des protocoles |

---

## Annexe A — Index des exigences

| Préfixe | Domaine |
|---------|---------|
| **E-** | Moteurs Qt / pygame / psychopy |
| **LL-** | Low-latency audio (PortAudio) |
| **F-** | Fonctionnel général (voir §5.1–5.10) |
| **V-** | **Présentation visuelle** (vidéo, image, formes, scènes générées) |
| **PY-** | **Tâches Python inline** (fichier `.py`, prepare/run) |
| **F-11xx** | Design expérimental |
| **F-12xx** | Affichage matériel (écran, Hz, multi-moniteur) |
| **F-13xx** | Médias fichiers (formats, chemins, hash) |
| **F-14xx** | Fiabilité / modes run |
| **F-15xx** | Sécurité / éthique |
| **F-16xx** | Extensions |
| **F-17xx** | Tests / observabilité |
| **S-** | JSON Schema |
| **NF-** | Non fonctionnel |

---

*Document vivant — v1.5 : §4.10 tâches Python inline (OpenSesame), nœud `python_task`, API `TaskContext`, exigences PY-*. Mettre à jour [MEMORY.md](./MEMORY.md) en résumé si changement majeur.*

