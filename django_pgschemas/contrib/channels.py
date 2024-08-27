from typing import cast

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.routing import URLRouter
from django.conf import settings
from django.urls import URLResolver, path
from django.utils.encoding import force_str
from django.utils.module_loading import import_string

from django_pgschemas.models import TenantModel as TenantModelBase
from django_pgschemas.routing.info import DomainInfo
from django_pgschemas.routing.urlresolvers import get_ws_urlconf_from_schema
from django_pgschemas.schema import Schema
from django_pgschemas.utils import get_domain_model, remove_www


def TenantURLRouter():
    async def router(scope, receive, send):
        if "tenant" not in scope:
            raise RuntimeWarning("`TenantURLRouter` must be wrapped by `DomainRoutingMiddleware`")

        routes = []

        schema: Schema = scope["tenant"]
        ws_urlconf = get_ws_urlconf_from_schema(schema) if schema else None

        if ws_urlconf:
            routes = import_string(ws_urlconf + ".urlpatterns")
            match routes:
                case [URLResolver()] if schema.routing.folder:
                    routes = [path(f"{schema.routing.folder}/", URLRouter(routes[0].urlconf_name))]
                case _:
                    pass

        _router = URLRouter(routes)
        return await _router(scope, receive, send)

    return router


class DomainRoutingMiddleware(BaseMiddleware):
    @database_sync_to_async
    def get_scope_tenant(self, scope):
        hostname = force_str(dict(scope["headers"]).get(b"host", b""))
        hostname = remove_www(hostname.split(":")[0])

        tenant: Schema | None = None

        # Checking for static tenants
        for schema, data in settings.TENANTS.items():
            if schema in ["public", "default"]:
                continue
            if hostname in data.get("DOMAINS", []):
                tenant = Schema.create(
                    schema_name=schema,
                    routing=DomainInfo(domain=hostname),
                )
                break

        # Checking for dynamic tenants
        else:
            DomainModel = get_domain_model()

            prefix = scope["path"].split("/")[1]
            domain = None

            if DomainModel is not None:
                try:
                    domain = DomainModel.objects.select_related("tenant").get(
                        domain=hostname, folder=prefix
                    )
                except DomainModel.DoesNotExist:
                    try:
                        domain = DomainModel.objects.select_related("tenant").get(
                            domain=hostname, folder=""
                        )
                    except DomainModel.DoesNotExist:
                        pass

            if domain is not None:
                tenant = cast(TenantModelBase, domain.tenant)
                tenant.routing = DomainInfo(domain=hostname)

                if prefix and domain.folder == prefix:
                    tenant.routing = DomainInfo(domain=hostname, folder=prefix)

        # Checking fallback domains
        if not tenant:
            for schema, data in settings.TENANTS.items():
                if schema in ["public", "default"]:
                    continue
                if hostname in data.get("FALLBACK_DOMAINS", []):
                    tenant = Schema.create(
                        schema_name=schema,
                        routing=DomainInfo(domain=hostname),
                    )
                    break

        return tenant

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["tenant"] = await self.get_scope_tenant(scope)

        return await super().__call__(scope, receive, send)
