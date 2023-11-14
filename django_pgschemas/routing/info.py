from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class DomainInfo:
    domain: str
    folder: str | None = None


@dataclass(frozen=True)
class SessionInfo:
    reference: str


@dataclass(frozen=True)
class HeadersInfo:
    reference: str


RoutingInfo: TypeAlias = DomainInfo | SessionInfo | HeadersInfo | None
