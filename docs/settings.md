## `TENANTS`

Default: `None`

The tenant configuration dictionary as explained in the [basic configuration](basic.md#database-configuration). A sample tenant configuration is:

```python
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
    "default": {
        "TENANT_MODEL": "tenants.Tenant",
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "customers",
        ],
        "URLCONF": "customers.urls",
        "CLONE_REFERENCE": "sample",
    }
}
```

## `PGSCHEMAS_EXTRA_SEARCH_PATHS`

Default: `[]`

Other schemas to include in Postgres search path. You cannot include the schema for any static or dynamic tenant. The public schema is included by default, so, including it here will raise `ImproperlyConfigured`.

## `PGSCHEMAS_LIMIT_SET_CALLS`

Default: `False`

By default, the search path is set every time a database cursor is required. In some intense situations, this could ralentize the queries. Set to `True` to limit the number of calls for setting the search path.

## `PGSCHEMAS_ORIGINAL_BACKEND`

Default: `"django.db.backends.postgresql"`

The base backend to inherit from. If you have a customized backend of Postgres, you can specify it here.

## `PGSCHEMAS_PARALLEL_MAX_PROCESSES`

Default: `None`

When `--parallel` is passed in any tenant command, this setting will control the max number of processes the parallel executor can spawn. By default, `None` means that the number of CPUs will be used.

## `PGSCHEMAS_TENANT_DB_ALIAS`

Default: `"default"`

The database alias where the tenant configuration is going to take place.

## `PGSCHEMAS_PATHNAME_FUNCTION`

Default: `None`

Function that takes a schema descriptor and returns a string identifier for the schema. This identifier will be used in the `TenantFileSystemStorage` as the name of the tenant folder.
