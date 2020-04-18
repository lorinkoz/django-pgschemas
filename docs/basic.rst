Installation
============

This app requires:

* python (3.6+)
* django (2.0+)
* psycopg2 (2.7+)

You can install ``django-pgschemas`` via ``pip``, ``poetry`` or any other
installer.

.. code-block:: bash

    pip install django-pgschemas
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
``TENANTS["public"]["TENANT_MODEL"]`` and routed through instances of
``TENANTS["public"]["DOMAIN_MODEL"]``.

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

Fast dynamic tenant creation
----------------------------

Every time a instance of ``settings.TENANTS["public"]["TENANT_MODEL"]`` is
created, by default, the corresponding schema is created and synchronized
automatically. Depending on the number of migrations you already have in place,
or the amount of time these could take, or whether you need to pre-populate the
newly created schema with fixtures, this process could take a considerable
amount of time.

If you need a faster creation of dynamic schemas, you can do so by provisioning
a "reference" schema that can cloned into new schemas.

.. code-block:: python

    TENANTS = {
        # ...
        "default": {
            # ...
            "CLONE_REFERENCE": "sample",
        },
    }

Once you have this in your settings, you need to prepare your reference schema
with everything a newly created dynamic schema will need. The first step is
actually creating and synchronizing the reference schema. After that, you
can run any command on it, or edit its tables via ``shell``.

.. code-block:: bash

    python manage.py createrefschema
    python runschema loaddata tenant_app.products -s sample
    python runschema shell -s sample

The ``runschema`` command is explained in :ref:`Management commands`.

You don't need any extra step. As soon as a reference schema is configured,
next time you create an instance of the tenant model, it will clone the
reference schema instead of actually creating and synchronizing the schema.

Most importantly, by default, migrations will include the reference schema, so
that it is kept up to date for future tenant creation.

.. attention::

    The database function for cloning schemas requires PostgreSQL 10 or higher,
    due to a change in the way sequence information is stored.


.. tip::

    The reference schema will get apps from
    ``settings.TENANTS["default"]["APPS"]`` and may look like any other dynamic
    tenant, but it is considered a *static* tenant instead, as there is no
    corresponding database entry for it. It's a special case of a static
    tenant, and it cannot be routed.
