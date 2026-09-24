# Protocoles manips (`examples/manips/`)

Inventaire **additif** : suite labo CerCo/ROSITO **et** manips du papier extrapolation.

## A. Papier extrapolation (Time / Chrono / Tone) — exécutables

| Dossier | Alias | Fichiers |
|---------|-------|----------|
| `spatiotemporelle` | Time | `protocol.json`, `protocol_chirurgie.json` |
| `nombre` | Chrono | idem |
| `son` | Tone | idem |

Moteur : `the_kit.manips.extrapolation` (mock en `--dry-run`).

```bash
for p in examples/manips/spatiotemporelle/protocol*.json \
         examples/manips/nombre/protocol*.json \
         examples/manips/son/protocol*.json; do
  uv run python -m the_kit validate -p "$p"
  uv run python -m the_kit run -p "$p" -s DEMO --dry-run
done
```

Sortie : `sessions/.../trials.csv` (1 essai / ligne).

## B. Suite labo (stubs / presets The Kit) — conservée

`arome`, `p1_p9_av_sync`, `audi_visuel`, `randomflow`, `shadowi`, `occultation`,
`occultation_ttc`, `mot`, `shadow_corridor_mot`, `neuroconn_gvs`, `ni_stim_alba`,
`looming_av`, `calibration_photosonde`

> **Correction** : ne jamais supprimer ces dossiers — The Kit **ajoute** des protocoles, ne retire pas les existants.

Voir `ASSETS.md` pour les chemins médias attendus (pas de fichiers inventés).
