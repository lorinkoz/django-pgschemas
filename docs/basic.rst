Installation
============

This app requires:

* Python (3.6+)
* Django (2.0+)
* Psycopg2 (2.7+)

You can install ``django-pgschemas`` via ``pip``, ``poetry`` or any other
installer.

.. code-block:: bash

    pip install django-pgschemas
    # or
    poetry add django-pgschemas

Basic Configuration
===================

Use ``django_pgschemas.postgresql_backend`` as your database engine. This
enables the API for setting PostgreSQL search path

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
        "django_pgschemas.middleware.TenantMiddleware",
        # ...
    )

Add ``django_pgschemas.routers.SyncRouter`` to your ``DATABASE_ROUTERS``, so
that the correct apps can be synced, depending on the target schema.

.. code-block:: python

    DATABASE_ROUTERS = (
        "django_pgschemas.routers.SyncRouter",
        # ...
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
        },
        # ...
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
        }
    }

Each entry in the ``TENANTS`` dictionary represents a static tenant, except for
``default``, which controls the settings for all dynamic tenants. Notice how
each tenant has the relevant ``APPS`` that will be synced in the corresponding
schema.

.. tip::

    ``public`` is always treated as shared schema and cannot be routed
    directly. Every other tenant will get its search path set to its schema
    first, then the public schema.

For Django to function properly, ``INSTALLED_APPS`` and ``ROOT_URLCONF``
settings must be defined. Just make them get their information from the
``TENANTS`` dictionary, for the sake of consistency.

.. code-block:: python

    INSTALLED_APPS = []
    for schema in TENANTS:
        INSTALLED_APPS += [app for app in TENANTS[schema]["APPS"] if app not in INSTALLED_APPS]

    ROOT_URLCONF = TENANTS["default"]["URLCONF"]


Creating tenants
----------------

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

Dynamic tenants need to be created through instances of
``TENANTS["default"]["TENANT_MODEL"]`` and routed through instances of
``TENANTS["default"]["DOMAIN_MODEL"]``.

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

Synchronizing tenants
---------------------

As a first step, you must always synchronize the public schema in order to get
the tenant and domain models created. You can then synchronize the rest of the schemas.

.. code-block:: bash

    python manage.py migrate -s public
    python manage.py migrate


Now you are ready to create your first dynamic tenant. In the example, the
tenant is created through a ``python manage.py shell`` session.

>>> from shared_app.models import Client, Domain
>>> client1 = Client.objects.create(schema_name="client1")
>>> Domain.objects.create(domain="client1.mydomain.com", tenant=client1, is_primary=True)
>>> Domain.objects.create(domain="clients.mydomain.com", folder="client1", tenant=client1)

Now any request made to ``client1.mydomain.com`` or
``clients.mydomain.com/client1/`` will automatically set
PostgreSQL's search path to ``client1`` and ``public``, making shared apps
available too. Also, at this point, any request to ``blog.mydomain.com`` or
``help.mydomain.com`` will set search path to ``blog`` and ``public``.

This means that any call to the methods ``filter``, ``get``, ``save``,
``delete`` or any other function involving a database connection will be done
at the correct schema, be it static or dynamic.
