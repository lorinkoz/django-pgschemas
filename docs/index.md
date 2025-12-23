# django-pgschemas

[![Build status](https://github.com/lorinkoz/django-pgschemas/workflows/code/badge.svg)](https://github.com/lorinkoz/django-pgschemas/actions)
[![Documentation status](https://readthedocs.org/projects/django-pgschemas/badge/?version=latest)](https://django-pgschemas.readthedocs.io/)
[![Code coverage](https://coveralls.io/repos/github/lorinkoz/django-pgschemas/badge.svg?branch=master)](https://coveralls.io/github/lorinkoz/django-pgschemas?branch=master)
[![PyPi version](https://badge.fury.io/py/django-pgschemas.svg)](http://badge.fury.io/py/django-pgschemas)
[![Downloads](https://pepy.tech/badge/django-pgschemas/month)](https://pepy.tech/project/django-pgschemas/)

---

This package uses Postgres schemas to support data multi-tenancy in a single Django project. Schemas are a layer of separation between databases and tables, so that one database can have multiple schemas, which in turn can have multiple (and possibly identical) tables. For an accurate description on schemas, see [the official documentation on Postgres schemas](http://www.postgresql.org/docs/9.1/static/ddl-schemas.html).

Postgres uses a "search path" to denote in which schemas it should look for the appropriate tables. If there are three schemas: `tenant1`, `common` and `public` and the search path is set to `["tenant1", "public"]`, Postgres will look for tables first on schema `tenant1`, and then, if not found, will look on schema `public`. The tables on schema `common` would never be searched. Also, if there is a table with the same name on both `tenant1` and `public` schemas (i.e. `django_migrations`), only the table in `tenant1` will be found by that search path. Table creation always takes place on the first schema in the search path.

`django-pgschemas`, as well as its predecessors `django-tenants` and `django-tenant-schemas`, takes advantage of Postgres schemas to emulate multi-tenancy, by mapping an incoming HTTP request to a specific schema, and setting the search path accordingly. It also provides an API to change the search path outside the request/response cycle, in order to perform schema-specific tasks.
