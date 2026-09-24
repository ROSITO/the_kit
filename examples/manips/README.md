# Protocoles manips (`examples/manips/`)

Inventaire **additif** : suite labo (13) + papier extrapolation (3).

## Papier Time / Chrono / Tone

Production : `trials_per_condition` / `n_essais_par_condition` = **15** (papier).  
`--dry-run` et `THE_KIT_EXTRAPOLATION_SMOKE=1` plafonnent à **1** essai/condition.

```bash
# Validate + dry-run (6 protocoles papier)
for p in examples/manips/spatiotemporelle/protocol*.json \
         examples/manips/nombre/protocol*.json \
         examples/manips/son/protocol*.json; do
  uv run python -m the_kit validate -p "$p"
  uv run python -m the_kit run -p "$p" -s DEMO --dry-run
done

# Session interactive (display + audio Tone)
uv sync --extra pygame --extra lowlatency
uv run python -m the_kit run -p examples/manips/spatiotemporelle/protocol.json -s S001
# Chirurgie : questions au lancement (ou THE_KIT_CHIRURGIE_ANSWERS='{...}')
uv run python -m the_kit run -p examples/manips/spatiotemporelle/protocol_chirurgie.json -s S001

# Headless pygame (CI / auto réponses)
SDL_VIDEODRIVER=dummy THE_KIT_EXTRAPOLATION_AUTO_INPUT=1 \
  uv run python -m the_kit run -p examples/manips/nombre/protocol.json -s AUTO

# Forcer N=15 même en smoke
THE_KIT_EXTRAPOLATION_FULL_N=1 uv run python -m the_kit run -p ... -s S001 --dry-run
```

Options secondaires : `secondary_option` 0|1|2 dans `script.args`.  
Sortie : `sessions/.../trials.csv`.

## Suite labo (stubs)

`arome`, `p1_p9_av_sync`, `audi_visuel`, `randomflow`, `shadowi`, `occultation`,
`occultation_ttc`, `mot`, `shadow_corridor_mot`, `neuroconn_gvs`, `ni_stim_alba`,
`looming_av`, `calibration_photosonde` — **ne pas supprimer**.
