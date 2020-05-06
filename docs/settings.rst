Settings
========

``TENANTS``
-----------

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
            "TENANT_MODEL": "shared_app.Client",
            "DOMAIN_MODEL": "shared_app.Domain",
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
--------------------------------

Default: ``[]``

Other schemas to include in PostgreSQL search path. You cannot include the
schema for any static or dynamic tenant. The public schema is included by
default, so, including it here will raise ``ImproperlyConfigured``.

``PGSCHEMAS_LIMIT_SET_CALLS``
-----------------------------

Default: ``False``

By default, the search path is set every time a database cursor is required. In
some intense situations, this could ralentize the queries. Set to ``True`` to
limit the number of calls for setting the search path.

``PGSCHEMAS_ORIGINAL_BACKEND``
------------------------------

Default: ``"django.db.backends.postgresql_psycopg2"``

The base backend to inherit from. If you have a customized backend of
PostgreSQL, you can specify it here.

``PGSCHEMAS_PARALLEL_MAX_PROCESSES``
------------------------------------

Default: ``None``

When ``--executor parallel`` is passed in any tenant command, this setting will
control the max number of processes the parallel executor can spawn. By
default, ``None`` means that the number of CPUs will be used.


``PGSCHEMAS_TENANT_DB_ALIAS``
-----------------------------

Default: ``"default"``

The database alias where the tenant configuration is going to take place.

``PGSCHEMAS_PATHNAME_FUNCTION``
-------------------------------

Default: ``None``

Function that takes a schema descriptor and returns a string identifier for the
schema. This identifier will be used in the ``TenantFileSystemStorage`` as the
name of the tenant folder.