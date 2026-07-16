# NeuroConn GVS + fNIRS

Protocole galvanique (carte NI → NeuroConn) avec enregistrement fNIRS via marqueurs LSL.

## Conditions (50 essais, 10 × 5)

| Condition | Direction | Trigger LSL (1× à l’onset) |
|-----------|-----------|----------------------------|
| AP | Avant | **2** |
| PA | Arrière | **3** |
| LATG | Gauche | **4** |
| LATD | Droite | **5** |
| CONTROL | Rampe mélangée | **6** |

Autres codes :

| Code | Événement |
|------|-----------|
| 1 | Début / fin de bloc |
| 8 | Réponse |

(Pas de trigger ITI ; un seul trigger condition par essai.)

Stream LabRecorder : **`Trigger`** (int32). Chaque envoi s’affiche dans le terminal (`🎯 LSL Trigger N`).

## Rampe

10 s : 3 s montée + 4 s plateau + 3 s descente. ITI = 10 + U(1,5) s.

## Lancement

```bash
uv sync --extra qt --extra pygame --extra ni
uv pip install pylsl
uv run python -m the_kit run -p examples/neuroconn_gvs/protocol_dryrun.json -s DRYRUN --dry-run
```

Sur poste labo : `"simulation_mode": false` (déjà le cas dans `protocol.json`).
**Sans ça, ou avec `--dry-run`, aucune tension n’est envoyée sur la carte NI.**

Au démarrage tu dois voir :
```text
NI-DAQ : connecté — Dev1/ao0, Dev1/ao1 @ 400.0 Hz
```
ou clairement `SIMULATION` / `ÉCHEC connexion`.

Pendant chaque essai :
```text
NI write ramp_AP: N=4000 dur=10.00s amp≈1.200V → carte
```

## Paramètres réglables

- `amplitude` — intensité unique (équivalent Alba, à calibrer en mA côté NeuroConn)
- `random_seed` — reproductibilité de l'ordre des 50 essais
