This package requires:

- Python (3.12+)
- Django (5.2+)
- Postgres (14+)
- Any version of psycopg.

## Installation

You can install `django-pgschemas` via `pip` or any other installer.

```bash
pip install django-pgschemas
```

## Database configuration

Use `django_pgschemas.postgresql` as your database engine. This enables the API for setting Postgres search path:

```python title="settings.py"
DATABASES = {
    "default": {
        "ENGINE": "django_pgschemas.postgresql",
        # more database configurations here
    }
}
```

Add `django_pgschemas.routers.TenantAppsRouter` to your `DATABASE_ROUTERS`, so that the proper migrations can be applied, depending on the target schema.

```python title="settings.py"
DATABASE_ROUTERS = (
    "django_pgschemas.routers.TenantAppsRouter",
    # additional routers here if needed
)
```

Define your tenant model.

```python title="tenants/models.py"
from django.db import models
from django_pgschemas.models import TenantModel

class Tenant(TenantModel):
    name = models.CharField(max_length=100)
    paid_until =  models.DateField(blank=True, null=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)
```

Add the minimal tenant configuration.

```python title="settings.py"
TENANTS = {
    "public": {
        "APPS": [
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django_pgschemas",
            "tenants",
        ],
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

Each entry in the `TENANTS` dictionary represents a static tenant, except for `default`, which controls the settings for all dynamic tenants. Notice how each tenant has the relevant `APPS` whose migrations will be applied in the corresponding schema.

For Django to function properly, `INSTALLED_APPS` and `ROOT_URLCONF` settings must be defined. Just make them get their information from the `TENANTS` dictionary, for the sake of consistency.

```python title="settings.py"
INSTALLED_APPS = []
for schema in TENANTS:
    INSTALLED_APPS += [
        app
        for app in TENANTS[schema]["APPS"]
        if app not in INSTALLED_APPS
    ]

ROOT_URLCONF = TENANTS["default"]["URLCONF"]
```

## Creating tenants

More static tenants can be added to the `TENANTS` dict.

```python title="settings.py"
TENANTS |= {
    "www": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "main",
        ],
        "URLCONF": "main.urls",
    },
    "blog": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "blog",
        ],
        "URLCONF": "blog.urls",
    },
}
```

And dynamic tenants can be added as well, programatically.

But first, you must always run migrations in the public schema in order to get the tenant model created. You can then migrate the rest of the schemas.

```bash
python manage.py migrate -s public
python manage.py migrate
```

Now you are ready to create your first dynamic tenant. In the example, the tenant is created through a `python manage.py shell` session.

```bash
>>> from tenants.models import Tenant
>>> Tenant.objects.create(schema_name="tenant_1")
```

This will automatically create a schema for the new dynamic tenant and apply migrations.

## Working with tenants

Because static and dynamic tenants can have their own Django apps configured, only the models within those apps will be migrated into their respective schemas. Without activating any tenant, the `public` schema will be the only schema in the search path, and therefore only models from the apps in `TENANTS["public"]["APPS"]` will be accessible.

For instance, after starting a new Django shell, querying the `Tenant` model will work, but querying models from other apps will raise a `ProgrammingError`:

```bash hl_lines="5 6"
>>> from tenants.models import Tenant
>>> from blog.models import BlogEntry
>>> from customers.models import Product
>>> Tenant.objects.all()
>>> BlogEntry.objects.all()  # ProgrammingError
>>> Product.objects.all()  # ProgrammingError
```

Before being able to operate in a tenant's schema, that tenant/schema must be activated first:

```bash hl_lines="1 5 8"
>>> from django_pgschemas.schemas import Schema
>>> from tenants.models import Tenant
>>> from blog.models import BlogEntry
>>> from customers.models import Product
>>> with Schema.create("blog"):
...     BlogEntry.objects.all()
>>> tenant1 = Tenant.objects.first()
>>> with tenant1:
...     Product.objects.all()
```

Tenant activation happens automatically during the request/response cycle through [tenant routing](routing.md).
