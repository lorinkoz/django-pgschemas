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

.. image:: https://api.travis-ci.org/lorinkoz/django-pgschemas.svg?branch=master
   :alt: Build status
   :target: https://travis-ci.org/lorinkoz/django-pgschemas

.. image:: https://readthedocs.org/projects/django-pgschemas/badge/?version=latest
    :alt: Documentation status
    :target: https://django-pgschemas.readthedocs.io/

.. image:: https://codecov.io/gh/lorinkoz/django-pgschemas/branch/master/graphs/badge.svg?branch=master
    :alt: Code coverage
    :target: https://codecov.io/gh/lorinkoz/django-pgschemas

.. image:: https://badge.fury.io/py/django-pgschemas.svg
    :alt: PyPi version
    :target: http://badge.fury.io/py/django-pgschemas

|

This app uses PostgreSQL schemas to support data multi-tenancy in a single
Django project. It is a fork of `django-tenants`_ with some conceptual changes:

- There are static tenants and dynamic tenants. Static tenants can have their
  own apps and urlconf.
- Tenants are routed both via subdomain and via subfolder on shared subdomain.
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
- Django's code of conduct applies to all means of contribution.
  https://www.djangoproject.com/conduct/.

Credits
-------

* Tom Turner for ``django-tenants``
* Bernardo Pires for ``django-tenant-schemas``
* Vlada Macek for ``django-schemata``
