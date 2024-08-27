from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter

from django_pgschemas.contrib.channels import DomainRoutingMiddleware, TenantURLRouter

application = ProtocolTypeRouter(
    {
        "websocket": DomainRoutingMiddleware(AuthMiddlewareStack(TenantURLRouter())),
    }
)
