# Exemples import Arôme

## Protocole minimal (sans médias)

```bash
cd ~/Documents/TheKit/the_kit
uv sync --extra qt
uv run python -m the_kit validate -p examples/arome_import/minimal_protocol.json
uv run python -m the_kit run -p examples/arome_import/minimal_protocol.json -s TEST --dry-run
```

## Protocole complet Arôme (vidéos + triggers)

Copier ou lier les assets depuis le projet Arôme :

```bash
cd examples/arome_import
# Option : symlink vers le dossier Arôme
ln -sf ~/Documents/Projet_Arome_ANAELLE/Projet_Arome_ANAELLE arome_root
```

Puis exécuter depuis `arome_root` (chemins relatifs `video/…`) :

```bash
cd arome_root   # ou Projet_Arome_ANAELLE
uv run python -m the_kit validate -p experiment9_notrig.json --check-media
uv run python -m the_kit run -p experiment9_notrig.json -s S001 --dry-run
```

`--dry-run` évite l’écriture série sur `COM4` (triggers simulés dans la console).

Sans `--dry-run`, un port série valide est requis pour les nœuds `trigger`.
