from __future__ import annotations

from pathlib import Path
from typing import Any

from the_kit.protocol.models import Protocol

NODE_TYPES = frozenset(
    {
        "video",
        "questionnaire",
        "trigger",
        "wait_key",
        "delay",
        "instructions",
        "blank",
        "av_sync",
        "audio",
        "keyboard_response",
        "optic_flow",
        "fixation",
        "shapes",
        "python_task",
        "slideshow",
        "block_break",
        "consent",
        "debrief",
        "photosonde_square",
        "shadow_ball",
        "occultation",
        "occultation_ttc",
        "mot",
        "psychopy_stim",
        "pygame_scene",
        "ni_stim",
        "neuroconn_gvs",
    }
)
ENGINES = frozenset({"qt", "pygame", "psychopy", "python"})

TYPE_DEFAULT_ENGINE = {
    "video": "qt",
    "questionnaire": "qt",
    "trigger": "qt",
    "wait_key": "qt",
    "delay": "qt",
    "instructions": "qt",
    "blank": "psychopy",
    "slideshow": "qt",
    "block_break": "qt",
    "consent": "qt",
    "debrief": "qt",
    "av_sync": "psychopy",
    "audio": "psychopy",
    "keyboard_response": "pygame",
    "optic_flow": "pygame",
    "fixation": "psychopy",
    "shapes": "psychopy",
    "python_task": "python",
    "photosonde_square": "psychopy",
    "shadow_ball": "pygame",
    "occultation": "pygame",
    "occultation_ttc": "psychopy",
    "mot": "pygame",
    "psychopy_stim": "psychopy",
    "pygame_scene": "pygame",
    "ni_stim": "python",
    "neuroconn_gvs": "pygame",
}


class ProtocolValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def validate_protocol(protocol: Protocol, *, check_media: bool = False) -> list[str]:
    errors: list[str] = []
    if not protocol.nodes and not (protocol.raw.get("conditions")):
        errors.append("Le protocole ne contient aucun nœud ni conditions[].")
    if not protocol.nodes and protocol.raw.get("conditions"):
        return []
    for node in protocol.nodes:
        if node.type not in NODE_TYPES:
            errors.append(
                f"Nœud {node.node_id}: type '{node.type}' inconnu "
                f"(types: {', '.join(sorted(NODE_TYPES))})."
            )
        if node.engine not in ENGINES:
            errors.append(
                f"Nœud {node.node_id}: engine '{node.engine}' inconnu "
                f"({', '.join(sorted(ENGINES))})."
            )
        expected = TYPE_DEFAULT_ENGINE.get(node.type)
        if expected and node.engine != expected:
            errors.append(
                f"Nœud {node.node_id}: type '{node.type}' attend engine '{expected}', "
                f"reçu '{node.engine}'."
            )
        if node.type == "video":
            fpath = node.params.get("file") or node.raw.get("file")
            if not fpath:
                errors.append(f"Nœud {node.node_id}: vidéo sans fichier ('file').")
            elif check_media:
                resolved = (protocol.root / fpath).resolve()
                if ".." in str(fpath):
                    errors.append(f"Nœud {node.node_id}: chemin non autorisé ({fpath}).")
                elif not resolved.exists():
                    errors.append(f"Nœud {node.node_id}: fichier introuvable ({resolved}).")
        if node.type == "questionnaire":
            questions = [k for k in node.params if k.startswith("question")]
            if not questions:
                errors.append(f"Nœud {node.node_id}: questionnaire sans questions.")
            if "echelle" not in node.params and "echelle" not in node.raw:
                errors.append(f"Nœud {node.node_id}: questionnaire sans 'echelle'.")
        if node.type == "av_sync":
            if not (node.params.get("video") or node.params.get("file")):
                errors.append(f"Nœud {node.node_id}: av_sync sans video.")
            if not node.params.get("audio"):
                errors.append(f"Nœud {node.node_id}: av_sync sans audio.")
            elif check_media:
                for key in ("video", "audio"):
                    rel = node.params.get(key) or node.params.get("file")
                    if rel and key == "video":
                        rel = node.params.get("video") or node.params.get("file")
                    if rel and not (protocol.root / rel).resolve().exists():
                        errors.append(f"Nœud {node.node_id}: {key} introuvable ({rel}).")
        if node.type == "python_task":
            script = node.params.get("script") or node.raw.get("script") or {}
            rel = script.get("file") if isinstance(script, dict) else None
            if not rel:
                errors.append(f"Nœud {node.node_id}: python_task sans script.file.")
            elif check_media and not (protocol.root / rel).resolve().exists():
                errors.append(f"Nœud {node.node_id}: script introuvable ({rel}).")
        if node.type == "slideshow":
            imgs = node.params.get("images") or node.params.get("files")
            if not imgs:
                errors.append(f"Nœud {node.node_id}: slideshow sans images.")
    if errors:
        raise ProtocolValidationError(errors)
    return []


def validate_protocol_file(path: str | Path, **kwargs: Any) -> Protocol:
    from the_kit.protocol.loader import load_protocol

    protocol = load_protocol(path)
    validate_protocol(protocol, **kwargs)
    return protocol


def try_json_schema(protocol: Protocol) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return []
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "protocol-v1.schema.json"
    if not schema_path.exists():
        return []
    import json

    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)
    try:
        jsonschema.validate(protocol.raw, schema)
    except jsonschema.ValidationError as e:
        return [str(e.message)]
    return []
