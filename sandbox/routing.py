from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter

from django_pgschemas.contrib.channels import TenantMiddleware, TenantURLRouter

application = ProtocolTypeRouter(
    {
        "websocket": TenantMiddleware(AuthMiddlewareStack(TenantURLRouter())),
    }
)
