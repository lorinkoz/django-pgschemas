django-pgschemas
================

.. image:: https://img.shields.io/badge/packaging-poetry-purple.svg
    :alt: Packaging: poetry
    :target: https://github.com/sdispater/poetry

.. image:: https://img.shields.io/badge/code%20style-black-black.svg
    :alt: Code style: black
    :target: https://github.com/ambv/black

.. image:: https://github.com/lorinkoz/django-pgschemas/workflows/code/badge.svg
    :alt: Build status
    :target: https://github.com/lorinkoz/django-pgschemas/actions

.. image:: https://readthedocs.org/projects/django-pgschemas/badge/?version=latest
    :alt: Documentation status
    :target: https://django-pgschemas.readthedocs.io/

.. image:: https://coveralls.io/repos/github/lorinkoz/django-pgschemas/badge.svg?branch=master
    :alt: Code coverage
    :target: https://coveralls.io/github/lorinkoz/django-pgschemas?branch=master

.. image:: https://badge.fury.io/py/django-pgschemas.svg
    :alt: PyPi version
    :target: http://badge.fury.io/py/django-pgschemas

.. image:: https://pepy.tech/badge/django-pgschemas/month
    :alt: Downloads
    :target: https://pepy.tech/project/django-pgschemas/

|

This app uses PostgreSQL schemas to support data multi-tenancy in a single
Django project. It is a fork of `django-tenants`_ with some conceptual changes:

- There are static tenants and dynamic tenants. Static tenants can have their
  own apps and urlconf.
- Tenants can be simultaneously routed via subdomain and via subfolder on shared
  subdomain.
- Public is no longer the schema for storing the main site data. Public should
  be used only for true shared data across all tenants. Table "overriding" via
  search path is no longer encouraged.
- Management commands can be run on multiple schemas via wildcards - the
  multiproc behavior of migrations was extended to just any tenant command.

.. _django-tenants: https://github.com/tomturner/django-tenants

Which package to use?
---------------------

There are currently multiple packages to handle multi-tenancy via PostgreSQL schemas.
This table should help you make an informed decision on which one to choose.

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Package
     - Features
   * - `django-tenant-schemas`_
     - Original project.
   * - `django-tenants`_
     - Built on top of `django-tenant-schemas`_.
       Uses a ``Domain`` model for allowing multiple domains per tenant.
       Allows for parallel migrations with custom migration executor.
       Other multiple improvements.
   * - `django-pgschemas`_
     - Built on top of `django-tenants`_.
       Different philosphy for tenants.
       Other improvements listed above.

.. _django-tenants-schemas: https://github.com/bernardopires/django-tenant-schemas
.. _django-tenants: https://github.com/tomturner/django-tenants
.. _django-pgschemas: https://github.com/lorinkoz/django-pgschemas

Documentation
-------------

https://django-pgschemas.readthedocs.io/

Breaking changes
----------------

v0.11.0
+++++++

- [INTERNAL] Now storing active schema in ``asgiref.local`` instead of the connection object.

v0.9.0
++++++

- Dropped support for Python < 3.8, Django < 3.1.

v0.7.0
++++++

- Changed public API for getting/setting active schema. Public API is now
  ``get_current_schema``, ``activate(schema)``, ``activate_public()``. Any
  schema descriptor can still be used as context manager.
- Changed location of tenant model and domain model in settings.
  ``TENANT_MODEL`` and ``DOMAIN_MODEL`` keys are now under ``TENANTS["default"]``
  instead of ``TENANTS["public"]``. This is required for future
  static-tenant-only configurations.
- Module ``cache`` renamed to ``contrib.cache``.
- Module ``contrib.channels`` renamed to ``contrib.channels2``.
- Added module ``contrib.channels3``.
- Management command option ``--executor {sequential, parallel}`` renamed to
  ``--parallel``.
- All signals renamed. Added ``schema_activate`` signal.

Contributing
------------

- Join the discussion at https://github.com/lorinkoz/django-pgschemas/discussions.
- PRs are welcome! If you have questions or comments, please use the link
  above.
- To run the test suite run ``make`` or ``make coverage``. The tests for this
  project live inside a small django project called ``dpgs_sandbox``. Database
  password and database host can be set through the environment variables
  ``DATABASE_PASSWORD`` and ``DATABASE_HOST``.

Credits
-------

* Tom Turner for `django-tenants`_
* Bernardo Pires for `django-tenant-schemas`_

.. _django-tenants: https://github.com/tomturner/django-tenants
.. _django-tenant-schemas: https://github.com/bernardopires/django-tenant-schemas
