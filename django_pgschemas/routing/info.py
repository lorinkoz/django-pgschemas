from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class DomainInfo:
    domain: str
    folder: str | None


@dataclass(frozen=True)
class SessionInfo:
    pass


@dataclass(frozen=True)
class HeadersInfo:
    pass


RoutingInfo: TypeAlias = DomainInfo | SessionInfo | HeadersInfo | None
