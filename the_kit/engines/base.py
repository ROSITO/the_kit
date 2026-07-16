from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node, Protocol


class EngineBase(ABC):
    name: str = "base"

    @abstractmethod
    def run(
        self,
        protocol: Protocol,
        session: SessionLogger,
        nodes: list[Node],
        *,
        dry_run: bool = False,
    ) -> None:
        ...

    def cleanup(self) -> None:
        """Libère fenêtre / flux audio du moteur."""

    @classmethod
    def check_available(cls) -> tuple[bool, str]:
        return True, "ok"
