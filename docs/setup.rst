Installation
============

Make sure you have the dependencies installed:

* python (3.5+)
* django = (2.0+)
* psycopg2-binary = (2.7+)

Install ``django-pgschemas``.

.. code-block:: bash

    pip install django-pgschemas

Basic Configuration
===================

Use ``django_pgschemas.postgresql_backend`` as your database engine.

.. code-block:: python

    DATABASES = {
        "default": {
            "ENGINE": "django_pgschemas.postgresql_backend",
            # ...
        }
    }

Add the middleware ``django_pgschemas.middleware.TenantMiddleware`` to the top
of ``MIDDLEWARE``, so that each request can be set to use the correct schema.

.. code-block:: python

    MIDDLEWARE = (
        "django_pgschemas.middleware.TenantMainMiddleware",
        #...
    )

Add ``django_pgschemas.routers.SyncRouter`` to your ``DATABASE_ROUTERS``, so
that the correct apps can be synced, depending on the target schema.

.. code-block:: python

    DATABASE_ROUTERS = (
        "django_pgschemas.routers.SyncRouter",
        #...
    )

Add the minimal tenant configuration.

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
        # ...
        "default": {
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "tenant_app",
                # ...
            ],
            "URLCONF": "tenant_app.urls",
        }
    }

Each entry in the ``TENANTS`` dictionary represents a static tenant, except for
``default``, which controls the settings for dynamic tenants (that is, database
controlled). ``public`` is always treated as shared schema and cannot be routed
directly.

For Django to function properly, ``INSTALLED_APPS`` and ``ROOT_URLCONF``
settings must be defined. Just make them get their information from the
``TENANTS`` dictionary, for the sake of consistency.

.. code-block:: python

    INSTALLED_APPS = []
    for schema in TENANTS:
        INSTALLED_APPS += [app for app in TENANTS[schema]["APPS"] if app not in INSTALLED_APPS]

    ROOT_URLCONF = TENANTS["default"]["URLCONF"]


Static tenants
--------------

More static tenants can be added and routed.

.. code-block:: python

    TENANTS = {
        # ...
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
        # ...
    }

Dynamic tenants
---------------

Dynamic tenants need to be created through instances of
``TENANTS["public"]["TENANT_MODEL"]``.

.. code-block:: python

    # shared_app/models.py

    from django.db import models
    from django_pgschemas.models import TenantMixin, DomainMixin

    class Client(TenantMixin):
        name = models.CharField(max_length=100)
        paid_until =  models.DateField(blank=True, null=True)
        on_trial = models.BooleanField(default=True)
        created_on = models.DateField(auto_now_add=True)

    class Domain(DomainMixin):
        pass

Sync the public schema, in order to get ``Client`` model created. Also sync
static schemas either one by one or using the ``:static:`` wildcard.

.. code-block:: bash

    python manage.py migrate_schemas -s public
    python manage.py migrate_schemas -s :static:

Create the first dynamic tenant.

>>> from shared_app.models import Client, Domain
>>> client1 = Client.objects.create(schema_name="client1")
>>> Domain.objects.create(domain="client1.mydomain.com", tenant=client1, is_primary=True)

Now any request made to ``client1.mydomain.com`` will automatically set
PostgreSQL's ``search_path`` to ``client1`` and ``public``, making shared apps
available too. Also, any request to blog.mydomain.com or
help.mydomain.com will set ``search_path`` to ``blog`` and ``public``. This
means that any call to the methods ``filter``, ``get``, ``save``, ``delete``
or any other function involving a database connection will now be done at the
correct schema, be it static or dynamic.
