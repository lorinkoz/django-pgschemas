All contributions and third party integrations live inside `django_pgschemas.contrib`.

If you want to implement an integration with other Django packages, please submit a pull request containing:

- The code for your integration.
- The tests for your integration.
- The docs for your integration in this section of the documentation.

We're striving to maintain/increase our code coverage, but please, make sure your integration is properly tested. Proper tests will always beat meaningless 100% coverage.

## Caching

In order to generate tenant aware cache keys, we provide `django_pgschemas.contrib.cache.make_key` which can be used as`KEY_FUNCTION`:

```python title="settings.py"
CACHES = {
    "default": {
        "KEY_FUNCTION": "django_pgschemas.contrib.cache.make_key",
    }
}
```

## Tenant aware file system storage

We provide a tenant aware file system storage at `django_pgschemas.contrib.storage.TenantFileSystemStorage`. It subclasses `django.core.files.storage.FileSystemStorage` and behaves like it in every aspect, except that it prepends a tenant identifier to the path and URL of all files.

By default, the tenant identifier is the schema name of the current tenant. In order to override this behavior, it is possible to provide a different identifier. The storage will consider these options when looking for an identifier:

- A method called `schema_pathname` in the current tenant. This method must accept no arguments and return an identifier.
- A function specified in a setting called `PGSCHEMAS_PATHNAME_FUNCTION`. This function must accept a `Schema` and return an identifier.
- Finally, the identifier will default to the schema name of the current tenant.

In the case of the URL returned from the storage, if the storage detects that the current schema has been routed via subfolder, it won't prepend the schema identifier, because it considers that the path is properly disambiguated as is. This means that instead of something like:

    /tenant1/static/tenant1/path/to/file.txt

It will generate:

    /tenant1/static/path/to/file.txt

This storage class is a convenient way of storing media files in a folder structure organized at the top by tenants, as well as providing a tenant centric organization in the URLs that are generated. However, this storage class does NOT provide any form of security, such as controlling that from one tenant, files from another tenant are not accessible. Such security requirements have other implications that fall out of the scope of this package.

!!! Tip

    In a project that requires airtight security you might want to use and customize [django-private-storage](https://github.com/edoburu/django-private-storage).

## Channels (websockets)

We provide some tenant middleware and a tenant URL router for using with `channels`. You can use it as follows:

```python title="routing.py"  hl_lines="12 14"
from channels.routing import ProtocolTypeRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django_pgschemas.contrib.channels import (
    DomainRoutingMiddleware, TenantURLRouter
)


application = ProtocolTypeRouter(
    {
        "websocket": AllowedHostsOriginValidator(
            DomainRoutingMiddleware(
                AuthMiddlewareStack(
                    TenantURLRouter()
                )
            )
        ),
    }
)
```

```python title="settings.py"
ASGI_APPLICATION = "routing.application"
```

There is also the `HeadersRoutingMiddleware` for headers-based routing.

The `TenantURLRouter` requires a urlconf for websockets:

```python title="settings.py" hl_lines="10"
TENANTS |= {
    "default": {
        "TENANT_MODEL": "tenants.Tenant",
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "customers",
        ],
        "URLCONF": "customers.urls",
        "WS_URLCONF": "customers.ws_urls",
    }
}
```

You still need to name your channel groups appropriately, taking the current tenant into account, if you want to keep your groups tenant-specific. The current tenant will be passed in `scope["tenant"]`.
