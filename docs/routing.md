Routing is the process of deciding to which tenant an incoming request belongs, and activating it for the rest of the request/response cycle. This is typically done via middleware and this package provides three routing mechanisms: domain, header and session routing.

The goal of these middleware is to augment the `request` object with tenant information. When these middleware are used the `request` will contain a `tenant` property with an instance of either the tenant model or the class `django_pgschemas.schema.Schema`.

## Domain routing

Tenants will have one or many domains (or subdomains), but each domain will correspond to only one tenant.

In this mechanism we use a database table to control domains per tenant. This domain model can be defined like this:

```python title="tenants/models.py"
from django_pgschemas.models import DomainModel

class Domain(DomainModel):
    pass
```

And added to the tenant settings like this:

```python title="settings.py" hl_lines="16 25 30"
TENANTS = {
    "public": {
        "APPS": [
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django_pgschemas",
            "tenants",
        ],
    },
    "www": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "main",
        ],
        "DOMAINS": ["mydomain.com"],
        "URLCONF": "main.urls",
    },
    "blog": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "blog",
        ],
        "DOMAINS": ["blog.mydomain.com", "help.mydomain.com"],
        "URLCONF": "blog.urls",
    },
    "default": {
        "TENANT_MODEL": "tenants.Tenant",
        "DOMAIN_MODEL": "tenants.Domain",
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "customers",
        ],
        "URLCONF": "customers.urls",
    }
}
```

Then you can assign domains to tenants:

```bash
>>> from tenants.models import Tenant, Domain
>>> tenant = Tenant.objects.create(schema_name="tenant_1")
>>> Domain.objects.create(tenant=tenant, domain="tenant1.mydomain.com")
```

!!! Note

    Notice that the `public` schema doesn't have `DOMAINS` configured. This is intentional. Attempting to add this key would result in an `ImproperlyConfigured` error. The public schema is non-routable by design.

Finally add `DomainRoutingMiddleware` to the top of the middleware stack, so that all subsequent middleware can benefit from the added tenant.

```python title="settings.py"
MIDDLEWARE = (
    "django_pgschemas.routing.middleware.DomainRoutingMiddleware",
    # other middleware
)
```

### Subfolder routing

It is also possible to use subfolder routing, instead of using domains/subdomains. In this case all tenants would share the same domain, but with a different "folder" component at the beginning of the requested path. The domain model supports this by default and allows for multiple combinations:

```bash
>>> from tenants.models import Tenant, Domain
>>> tenant = Tenant.objects.create(schema_name="tenant_1")
>>> Domain.objects.create(
...     tenant=tenant,
...     domain="tenant1.mydomain.com",
...     is_primary=True,
... )
>>> Domain.objects.create(
...     tenant=tenant,
...     domain="tenants.mydomain.com",
...     folder="tenant1",
... )
```

!!! Warning

    Subfolder routing is currently not supported for static tenants.

For a special case with subfolder routing please see [fallback domains](advanced.md#fallback-domains).

## Header routing

In this mechanism a request header is defined to pass the tenant database ID or the schema name.

```python title="settings.py"
PGSCHEMAS_TENANT_HEADER = "tenant"
```

Static tenants can be routed using the `HEADER` key in the `TENANTS` settings:

```python title="settings.py" hl_lines="16 25"
TENANTS = {
    "public": {
        "APPS": [
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django_pgschemas",
            "tenants",
        ],
    },
    "www": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "main",
        ],
        "HEADER": "main",
        "URLCONF": "main.urls",
    },
    "blog": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "blog",
        ],
        "HEADER": "blog",
        "URLCONF": "blog.urls",
    },
    "default": {
        "TENANT_MODEL": "tenants.Tenant",
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "customers",
        ],
        "URLCONF": "customers.urls",
    }
}
```

!!! Note

    Notice that the `public` schema doesn't have `HEADER` configured. This is intentional. Attempting to add this key would result in an `ImproperlyConfigured` error. The public schema is non-routable by design.

Then add `HeadersRoutingMiddleware` to the top of the middleware stack.

```python title="settings.py"
MIDDLEWARE = (
    "django_pgschemas.routing.middleware.HeadersRoutingMiddleware",
    # other middleware
)
```

## Session routing

In this mechanism a session key is defined to store the tenant database ID or the schema name.

```python title="settings.py"
PGSCHEMAS_TENANT_SESSION_KEY = "tenant"
```

Static tenants can be routed using the `SESSION_KEY` key in the `TENANTS` settings:

```python title="settings.py" hl_lines="16 25"
TENANTS = {
    "public": {
        "APPS": [
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django_pgschemas",
            "tenants",
        ],
    },
    "www": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "main",
        ],
        "SESSION_KEY": "main",
        "URLCONF": "main.urls",
    },
    "blog": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "blog",
        ],
        "SESSION_KEY": "blog",
        "URLCONF": "blog.urls",
    },
    "default": {
        "TENANT_MODEL": "tenants.Tenant",
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "customers",
        ],
        "URLCONF": "customers.urls",
    }
}
```

!!! Note

    Notice that the `public` schema doesn't have `SESSION_KEY` configured. This is intentional. Attempting to add this key would result in an `ImproperlyConfigured` error. The public schema is non-routable by design.

Then add `SessionRoutingMiddleware` to the top of the middleware stack, but after the session middleware.

```python title="settings.py"
MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_pgschemas.routing.middleware.SessionRoutingMiddleware",
    # other middleware
)
```
