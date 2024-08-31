There are typically three solutions for solving the multi-tenancy problem.

1. Isolated approach: Separate databases. Each tenant has its own database.
2. Semi-isolated approach: Shared database, separate schemas. One database for all tenants, but one schema per tenant.
3. Shared approach: Shared database, shared schema. All tenants share the same database and schema. There is a main tenant-table, where all other tables have a foreign key pointing to.

Each solution has its up and down sides, for a more in-depth discussion, see Microsoft's excellent article on [Multi-Tenant Data Architecture](https://docs.microsoft.com/en-us/azure/sql-database/saas-tenancy-app-design-patterns).

This package implements the second approach, which in our opinion, represents a good compromise between simplicity and performance.

!!! Tip

    If you are looking for an implementation of the third approach, you might be interested in [django-multitenant](https://github.com/citusdata/django-multitenant). For other solutions of the multi-tenancy problem, you could also look [here](https://djangopackages.org/grids/g/multi-tenancy/).

The semi-isolated approach through Postgres schemas has some advantages and disadvantages:

- Simplicity: barely make any changes to your current code to support multi-tenancy. Plus, you only manage one database.
- Performance: make use of shared connections, buffers and memory.

vs.

- Scalability: for a large number of tenants (thousands) the schema approach might not be feasible, and as of now, there is no clear way for implementing tenant sharding.

## Schemas vs. Tenants

The terms _schema_ and _tenant_ are used indistinctly all over the documentation. However, it is important to note some subtle differences between the two. We consider a _tenant_ to be a subset of isolated data, and we use database _schemas_ for that purpose. Still, there can be schemas that cannot be considered tenants according to our definition. One good example is the `public` schema, which contains data shared across all tenants. Therefore every tenant is a schema, but not every schema is a tenant.

## Static vs. Dynamic

In a typical software-as-a-service (SaaS), there can be a group of static sites that are related to enterprise level operations. For instance, a site where customers can enter payment information and sign up for a tenant, or an enterprise content management system. These sites are generally well defined at the time of developing the web application.

On the other hand, there are the sites of the customers that will sign up of the SaaS. The specific information for these sites is dynamic in nature, because it cannot be determined at the time of developing the application.

This package allows you to manage both static and dynamic tenants. Static tenants are defined through Django settings, whereas dynamic tenants are stored in specific tables in the database.

## Users and tenants

One of the most important architectural decisions that you must make before implementing a SaaS is to define the relationship between users and tenants. There are three possible approaches:

- Users exist outside of tenants and can be granted access to specific tenants: this means that the user registers once and can be assigned to different tenants with different permissions on those tenants.
- Users are confined within a tenant: this means that users must be created inside a tenant and cannot be part of more than one tenant. If the same person needs to be member of multiple tenants, they need different users.
- Users are tenants: a tenant can only have one user. This is a special case of the previous approach.
