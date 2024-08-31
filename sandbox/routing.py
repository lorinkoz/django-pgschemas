from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter

from django_pgschemas.contrib.channels import (
    DomainRoutingMiddleware,
    HeadersRoutingMiddleware,
    TenantURLRouter,
)

domain_application = ProtocolTypeRouter(
    {
        "websocket": DomainRoutingMiddleware(
            AuthMiddlewareStack(
                TenantURLRouter(),
            ),
        ),
    }
)

headers_application = ProtocolTypeRouter(
    {
        "websocket": HeadersRoutingMiddleware(
            AuthMiddlewareStack(
                TenantURLRouter(),
            ),
        ),
    }
)

application = domain_application
