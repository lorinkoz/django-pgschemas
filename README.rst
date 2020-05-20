django-pgschemas
================

.. image:: https://img.shields.io/badge/packaging-poetry-purple.svg
    :alt: Packaging: poetry
    :target: https://github.com/sdispater/poetry

.. image:: https://img.shields.io/badge/code%20style-black-black.svg
    :alt: Code style: black
    :target: https://github.com/ambv/black

.. image:: https://badges.gitter.im/Join%20Chat.svg
    :alt: Join the chat at https://gitter.im/django-pgschemas
    :target: https://gitter.im/django-pgschemas/community?utm_source=share-link&utm_medium=link&utm_campaign=share-link

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
    :target: https://pepy.tech/project/django-pgschemas/month

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


Documentation
-------------

https://django-pgschemas.readthedocs.io/

Contributing
------------

- Join the discussion at https://gitter.im/django-pgschemas/community.
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
