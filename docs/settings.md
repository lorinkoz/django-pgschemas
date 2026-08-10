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

Other schemas to include in Postgres search path. You cannot include the schema for any static or dynamic tenant. The public schema is included by default, so including it here will raise system check `pgschemas.W005` (database-tagged; see [troubleshooting](troubleshooting.md)).

## `PGSCHEMAS_LIMIT_SET_CALLS`

Default: `False`

By default, the search path is set every time a database cursor is required. In some intense situations, this could slow down the queries. Set to `True` to limit the number of calls for setting the search path.

!!! Warning

    `PGSCHEMAS_LIMIT_SET_CALLS=True` is unsafe with transaction-pooling PgBouncer (or similar), because the cached search path may not match the connection handed out for the next request.

## `PGSCHEMAS_ORIGINAL_BACKEND`

Default: `"django.db.backends.postgresql"`

The base backend to inherit from. If you have a customized backend of Postgres, you can specify it here.

## `PGSCHEMAS_PARALLEL_MAX_THREADS`

Default: `None`

When `--parallel` is passed in any tenant command, this setting controls the max number of threads the parallel executor (`ThreadPoolExecutor`) can use. By default, `None` means the number of CPUs will be used.

## `PGSCHEMAS_TENANT_DB_ALIAS`

Default: `"default"`

The database alias where the tenant configuration is going to take place.

## `PGSCHEMAS_TENANT_HEADER`

Default: `"tenant"`

HTTP header name used by header-based routing to select a tenant. See [routing](routing.md#header-routing) for the trust model and security warnings.

## `PGSCHEMAS_TENANT_SESSION_KEY`

Default: `"tenant"`

Session key used by session-based routing to select a tenant. See [routing](routing.md#session-routing) for setup notes.

## `PGSCHEMAS_PATHNAME_FUNCTION`

Default: `None`

Function that takes a schema descriptor and returns a string identifier for the schema. This identifier will be used in the `TenantFileSystemStorage` as the name of the tenant folder.
