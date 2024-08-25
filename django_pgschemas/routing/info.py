from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class DomainInfo:
    domain: str
    folder: str | None = None

    def __str__(self) -> str:
        return f"{self.domain}/{self.folder}" if self.folder else self.domain


@dataclass(frozen=True)
class SessionInfo:
    reference: str

    def __str__(self) -> str:
        return f"Session: {self.reference}"


@dataclass(frozen=True)
class HeadersInfo:
    reference: str

    def __str__(self) -> str:
        return f"Header: {self.reference}"


RoutingInfo: TypeAlias = DomainInfo | SessionInfo | HeadersInfo | None
