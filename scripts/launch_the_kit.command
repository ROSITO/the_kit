#!/bin/bash
# Double-clic macOS — lance l'interface The Kit (sélection protocole + run).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv requis : https://docs.astral.sh/uv/" >&2
  read -r -p "Appuyez sur Entrée pour fermer…"
  exit 1
fi
uv sync --extra qt --extra pygame --extra lowlatency
exec uv run python -m the_kit launch
