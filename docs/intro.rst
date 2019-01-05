Introduction
============

This app uses PostgreSQL schemas to support data multi-tenancy in a single
Django project. Schemas are a layer of separation between databases and tables,
so that one database can have multiple schemas, which in turn can have multiple
(and possibly identical) tables. For an accurate description on schemas, see
`the official documentation on PostgreSQL schemas`_.

.. _the official documentation on PostgreSQL schemas: http://www.postgresql.org/docs/9.1/static/ddl-schemas.html

PostgreSQL uses a "search path" to denote in which schemas it should look for
the appropriate tables. If there are three schemas: ``client1``, ``common`` and
``public`` and the search path is set to ``["client1", "public"]``, PostgreSQL
will look for tables first on schema ``client1``, and then, if not found, will
look on schema ``public``. The tables on schema ``common`` would never be
searched. Also, if there is a table with the same name on both ``client1`` and
``public`` schemas (i.e. ``django_migrations``), only the table in ``client1``
will be found by that search path.  Table creation always takes place on the
first schema in the search path.

``django-pgschemas``, as well as it's predecessors ``django-tenants`` and
``django-tenant-schemas``, takes advantage of PostgreSQL schemas to emulate
multi-tenancy, by mapping certain URL patterns to schemas, and setting the
search path accordingly. It also provides an API to smartly change the search
path outside the request/response cycle, in order to perform schema-specific
tasks.

Multi-tenancy
-------------

There are typically three solutions for solving the multi-tenancy problem.

1. Isolated approach: Separate databases. Each tenant has it's own database.

2. Semi-isolated approach: Shared database, separate schemas. One database for
   all tenants, but one schema per tenant.

3. Shared approach: Shared database, shared schema. All tenants share the same
   database and schema. There is a main tenant-table, where all other tables
   have a foreign key pointing to.

Each solution has its up and down sides, for a more in-depth discussion, see
Microsoft's excellent article on `Multi-Tenant Data Architecture`_.

.. _Multi-Tenant Data Architecture: http://msdn.microsoft.com/en-us/library/aa479086.aspx

This application implements the second approach, which in our opinion,
represents a good compromise between simplicity and performance.

.. tip::

    If you are looking for an implementation of the third approach, you might be
    interested in `this package`_. For other solutions of the multi-tenancy
    problem, you could also look `here`_.

.. _this package: https://github.com/cistusdata/django-multitenant
.. _here: https://djangopackages.org/grids/g/multi-tenancy/

The semi-isolated approach through PostgreSQL schemas has some advantages and
disadvantages:

* Simplicity: barely make any changes to your current code to support
  multi-tenancy. Plus, you only manage one database.
* Performance: make use of shared connections, buffers and memory.

vs.

* Scalability: for a large number of tenants (thousands) the schema approach
  might not be feasible, and as of now, there is no clear way for implementing
  tenant sharding.

Schemas vs. Tenants
-------------------

The terms *schema* and *tenant* are used indistinctly all over the
documentation. However, it is important to note some subtle differences between
the two. We consider a *tenant* to be a subset of data that can be accessed
with a URL (routed), and we use database *schemas* for that purpose. Still,
there can be schemas that shouldn't be considered tenants according to our
definition. One good example is the ``public`` schema, which most typically
contains data shared across all tenants. Then, every tenant is a schema, but
not every schema is a tenant.

Static vs. Dynamic
------------------

In a typical software-as-a-service (SaaS), there is a number of static sites
that are related to enterprise level operations. Using ``mydomain.com`` as
example, one could think of these enterprise level sites::

    mydomain.com
    www.mydomain.com
    blog.mydomain.com
    help-center.mydomain.com

Likewise, there are going to be multiple sites for tenant specific operations.
Those sites are dynamic in nature, as cannot be determined at the time of
implementation -- and hopefully, will be thousands ;) The dynamic sites could
follow a subdomain routing approach like::

    customer1.mydomain.com
    customer2.mydomain.com

A subfolder routing approach like::

    customers.mydomain.com/customer1
    customers.mydomain.com/customer2

Or a mixed approach, where even a-la-carte domains are used (say, for VIP
clients) like::

    customer1.mydomain.com
    customers.mydomain.com/customer1
    customers.mydomain.com/customer2
    www.thevipcustomer.com

This app allows you to manage both static and dynamic tenants, and the three
kinds of routing.

.. attention::

    For static tenants, only the subdomain routing is available.

In order to manage dynamic tenants, we provide two model mixins you must
inherit in your models: ``TenantMixin`` and ``DomainMixin``. The former
controls the tenants and the latter controls the domain/folder combinations
that will route each tenant.