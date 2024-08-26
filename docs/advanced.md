## Fast dynamic tenant creation

Every time a instance of the tenant model is created, by default, the corresponding schema is created and synchronized automatically. Depending on the number of migrations you already have in place, or the amount of time these could take, or whether you need to pre-populate the newly created schema with fixtures, this process could take a considerable amount of time.

If you need a faster creation of dynamic schemas, you can do so by provisioning a "reference" schema that can cloned into new schemas.

```python title="settings.py" hl_lines="10"
TENANTS |= {
    "default": {
        "TENANT_MODEL": "tenants.Tenant",
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "customers",
        ],
        "URLCONF": "customers.urls",
        "CLONE_REFERENCE": "sample",
    }
}
```

Once you have this in your settings, you need to prepare your reference schema with everything a newly created dynamic schema will need. The first step consists of creating and applying migrations to the reference schema. After that, you can run any command on it or even edit its tables via `shell`.

```bash
python manage.py createrefschema
python runschema loaddata customers.products -s sample
python runschema shell -s sample
```

The `runschema` command is explained in [running management commands](#running-management-commands).

You don't need any extra step. As soon as a reference schema is configured, the next time you create an instance of the tenant model, it will clone the reference schema instead of actually creating and synchronizing the schema.

!!! Note

    The reference schema looks like a dynamic tenant, but it's actually static. It is also non-routable by design.

## Fallback domains

If there is only one domain available, and no possibility to use subdomain routing, the URLs for accessing your different tenants might look like:

    mydomain.com                -> main site
    mydomain.com/customer1      -> customer 1
    mydomain.com/customer2      -> customer 2

In this case, due to the order in which domains are tested, it is not possible to put `mydomain.com` as domain for the main tenant without blocking all dynamic schemas from getting routed. When `django_pgschemas.middleware.TenantMiddleware` is checking which tenant to route from the incoming domain, it checks for static tenants first, then for dynamic tenants. If `mydomain.com` is used for the main tenant (which is static), then URLs like `mydomain.com/customer1/some/url/` will match the main tenant always.

For a case like this, we provide a setting called `FALLBACK_DOMAINS`. If no tenant is found for an incoming combination of domain and subfolder, then, static tenants are checked again for the fallback domains.

Something like this would be the proper configuration for the present case:

```python title="settings.py" hl_lines="16 17"
TENANTS = {
    "public": {
        "APPS": [
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django_pgschemas",
            "tenants",
        ],
    },
    "main": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "main",
        ],
        "DOMAINS": [],
        "FALLBACK_DOMAINS": ["mydomain.com"],
        "URLCONF": "main.urls",
    },
    "default": {
        "TENANT_MODEL": "tenants.Tenant",
        "DOMAIN_MODEL": "tenants.Domain",
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "customers",
        ],
        "URLCONF": "customers.urls",
    }
}
```

This example assumes that dynamic tenants will get their domains set to `mydomain.com` with a tenant specific subfolder, like `tenant1` or `tenant2`.

Here, an incoming request for `mydomain.com/tenant1/some/url/` will fail for the main tenant, then match against an existing dynamic tenant.

On the other hand, an incoming request for `mydomain.com/some/url/` will fail for all static tenants, then fail for all dynamic tenants, and will finally match against the fallback domains of the main tenant.

## Static tenants only

It's also possible to have only static tenants and no dynamic tenants at all. For this, the default key must be omitted altogether:

```python title="settings.py"
TENANTS = {
    "public": {
        "APPS": [
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django_pgschemas",
            "tenants",
        ],
    },
    "www": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "main",
        ],
        "DOMAINS": ["mydomain.com"],
        "URLCONF": "main.urls",
    },
    "blog": {
        "APPS": [
            "django.contrib.auth",
            "django.contrib.sessions",
            "blog",
        ],
        "DOMAINS": ["blog.mydomain.com", "help.mydomain.com"],
        "URLCONF": "blog.urls",
    }
}
```

In this case, no model is expected to inherit from `TenantModel` and `DomainModel`, and no clone reference schema can be created.

## Running management commands

Since all management commands occur outside the request/response cycle, all commands from Django and any other third party apps are executed by default on the public schema. In order to work around this, we provide a `runschema` command that accepts any other command to be run on one or multiple schemas. A concise synopsis of the `runschema` command is as follows:

    usage: manage.py runschema [-s SCHEMAS [SCHEMAS ...]]
                            [-x EXCLUDED_SCHEMAS [EXCLUDED_SCHEMAS ...]]
                            [-as] [-ss] [-ds] [-ts]
                            [--parallel]
                            [--no-create-schemas]
                            [--noinput]
                            command_name

    Wrapper around django commands for use with an individual schema

    positional arguments:
    command_name          The command name you want to run

    optional arguments:

    --noinput, --no-input
                        Tells Django to NOT prompt the user for input of any
                        kind.

    -s SCHEMAS [SCHEMAS ...],
    --schema SCHEMAS [SCHEMAS ...]
                        Schema(s) to execute the current command
    -as, --include-all-schemas
                        Include all schemas when executing the current command
    -ss, --include-static-schemas
                        Include all static schemas when executing the current
                        command
    -ds, --include-dynamic-schemas
                        Include all dynamic schemas when executing the current
                        command
    -ts, --include-tenant-schemas
                        Include all tenant-like schemas when executing the
                        current command
    -x EXCLUDED_SCHEMAS [EXCLUDED_SCHEMAS ...],
    --exclude-schema EXCLUDED_SCHEMAS [EXCLUDED_SCHEMAS ...]
                        Schema(s) to exclude when executing the current
                        command

    --parallel          Run command in parallel mode
    --no-create-schemas
                        Skip automatic creation of non-existing schemas

The `--schema` parameter accepts multiple inputs of different kinds:

- The key of a static tenant or the `schema_name` of a dynamic tenant.
- The prefix of any domain, provided only one corresponding tenant is found.
- The prefix of any `domain/folder` of a tenant, like `tenants.mydomain.com/tenant1`

The parameters `-as`, `-ss`, `-ds` and `-ts` act as wildcards for including all schemas, static schemas, dynamic schemas and tenant-like schemas, respectively. Tenant-like schemas are dynamic schemas plus the clone reference, if it exists.

It's possible to exclude schemas via the `-x` parameter. Excluded schemas will take precedence over included ones.

At least one schema is mandatory. If it's not provided with the command, either explicitly or via wildcard params, it will be asked interactively. One notable exception to this is when the option `--noinput` is passed, in which case the command will fail.

If `--parallel` is passed, the command will be run asynchronously, spawning multiple threads controlled by the setting `PGSCHEMAS_PARALLEL_MAX_PROCESSES`. It defaults to `None`, in which case the number of CPUs will be used.

By default, schemas that do not exist will be created (but not synchronized), except if `--no-create-schemas` is passed.

Full details for this command can be found in :ref:`runschema-cmd`.

### Inheritable commands

We also provide some base commands you can inherit, in order to mimic the behavior of `runschema`. By inheriting these you will get the parameters we discussed in the previous section. The base commands provide a `handle_tenant` you must override in order to execute the actions you need on any given tenant.

The base commands are:

```python title="django_pgschemas/management/commands/__init__.py"
class SchemaCommand(WrappedSchemaOption, BaseCommand):

    def handle_schema(self, schema, *args, **options):
        pass

class StaticSchemaCommand(SchemaCommand):
    ...

class DynamicSchemaCommand(SchemaCommand):
    ...
```

!!! Warning

    Since these commands can work with the schemas of static and dynamic tenants, the parameter `schema` will be an instance of `django_pgschemas.schema.Schema`. Make sure to do the appropriate type checking before accessing the tenant members, as not always you will get an instance of the tenant model.
