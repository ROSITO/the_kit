from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node


@dataclass
class SceneContext:
    """Contexte partagé fond + stimuli pour un nœud pygame_scene."""

    node: Node
    session: SessionLogger
    screen: Any
    clock: Any
    width: int
    height: int
    elapsed_s: float = 0.0
    variables: dict[str, Any] = field(default_factory=dict)

    def log(self, event: str, **payload: Any) -> None:
        self.session.log_event(
            event,
            node_id=self.node.node_id,
            node_type=self.node.type,
            node_index=self.node.index,
            engine=self.node.engine,
            payload=payload or None,
        )
