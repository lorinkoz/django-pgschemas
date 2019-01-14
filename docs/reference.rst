Reference
=========

Models
------

``TenantMixin``
+++++++++++++++

.. autoclass:: django_pgschemas.models.TenantMixin
    :members: auto_create_schema, auto_drop_schema, create_schema, drop_schema

``DomainMixin``
+++++++++++++++

.. autoclass:: django_pgschemas.models.DomainMixin

Settings
--------

``TENANTS``
+++++++++++

Default: ``None``

The tenant configuration dictionary as explained in :ref:`Basic configuration`.
A sample tenant configuration is:

.. code-block:: python

    TENANTS = {
        "public": {
            "APPS": [
                "django.contrib.contenttypes",
                "django.contrib.staticfiles",
                # ...
                "django_pgschemas",
                "shared_app",
                # ...
            ],
            "TENANT_MODEL": "shared_app.Client",
            "DOMAIN_MODEL": "shared_app.Domain",
        },
        "www": {
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "main_app",
            ],
            "DOMAINS": ["mydomain.com"],
            "URLCONF": "main_app.urls",
        },
        "blog": {
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "blog_app",
            ],
            "DOMAINS": ["blog.mydomain.com", "help.mydomain.com"],
            "URLCONF": "blog_app.urls",
        },
        "default": {
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "tenant_app",
                # ...
            ],
            "URLCONF": "tenant_app.urls",
            "CLONE_REFERENCE": "sample",
        }
    }

``PGSCHEMAS_EXTRA_SEARCH_PATHS``
++++++++++++++++++++++++++++++++

Default: ``[]``

Other schemas to include in PostgreSQL search path. You cannot include the
schema for any static or dynamic tenant. The public schema is included by
default, so, including it here will raise ``ImproperlyConfigured``.

``PGSCHEMAS_LIMIT_SET_CALLS``
+++++++++++++++++++++++++++++

Default: ``False``

By default, the search path is set every time a database cursor is required. In
some intense situations, this could ralentize the queries. Set to ``True`` to
limit the number of calls for setting the search path.

``PGSCHEMAS_ORIGINAL_BACKEND``
++++++++++++++++++++++++++++++

Default: ``"django.db.backends.postgresql_psycopg2"``

The base backend to inherit from. If you have a customized backend of
PostgreSQL, you can specify it here.

``PGSCHEMAS_PARALLEL_MAX_PROCESSES``
++++++++++++++++++++++++++++++++++++

Default: ``None``

When ``--executor parallel`` is passed in any tenant command, this setting will
control the max number of processes the parallel executor can spawn. By
default, ``None`` means that the number of CPUs will be used.


``PGSCHEMAS_TENANT_DB_ALIAS``
+++++++++++++++++++++++++++++

Default: ``"default"``

The database alias where the tenant configuration is going to take place.

Utils
-----

.. automodule:: django_pgschemas.utils
    :members: get_tenant_model, get_domain_model, is_valid_identifier,
        is_valid_schema_name, check_schema_name, remove_www,
        run_in_public_schema, schema_exists, dynamic_models_exist,
        create_schema, drop_schema, clone_schema, create_or_clone_schema
