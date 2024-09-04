## Fast dynamic tenant creation

Every time a instance of the tenant model is created, by default, the corresponding schema is created and migrations are applied automatically. Depending on the number of migrations you already have in place, or the amount of time these could take, or whether you need to pre-populate the newly created schema with fixtures, this process could take a considerable amount of time.

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

You don't need any extra step. As soon as a reference schema is configured, the next time you create an instance of the tenant model, it will clone the reference schema instead of actually creating the schema and applying all migrations.

!!! Note

    The reference schema looks like a dynamic tenant, but it is actually static. It is also non-routable by design.

!!! Warning

    This package relies on [denishpatel/pg-clone-schema](https://github.com/denishpatel/pg-clone-schema/) for the schema cloning functionality.

## Fallback domains

If there is only one domain available, and no possibility to use subdomain routing, the URLs for accessing your different tenants might look like this:

| URL                    | Tenant    |
| ---------------------- | --------- |
| `mydomain.com`         | Main site |
| `mydomain.com/tenant1` | Tenant 1  |
| `mydomain.com/tenant2` | Tenant 2  |

In this case, due to the order in which domains are tested, it is not possible to put `mydomain.com` as domain for the main tenant without blocking all dynamic schemas from getting routed. When `django_pgschemas.routing.middleware.DomainRoutingMiddleware` is checking which tenant to route from the incoming domain, it checks for static tenants first, then for dynamic tenants. If `mydomain.com` is used for the main tenant (which is static), then URLs like `mydomain.com/tenant1/some/url/` will match the main tenant always.

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

Since all management commands occur outside the request/response cycle, all commands from Django and any other third party apps are executed by default on the public schema. In order to work around this, we provide a `runschema` command that accepts any other command to be run on one or multiple schemas. A minimal synopsis of the `runschema` command is as follows:

```bash
usage: manage.py runschema [-s SCHEMAS [SCHEMAS ...]]
                        [-x EXCLUDED_SCHEMAS [EXCLUDED_SCHEMAS ...]]
                        [-as] [-ss] [-ds] [-ts]
                        [--parallel]
                        [--no-create-schemas]
                        [--noinput]
                        command_name
```

The `-s --schema` argument accepts multiple inputs of different kinds:

- The key of a static tenant or the `schema_name` of a dynamic tenant.
- The prefix of any domain, as long as only one tenant is found.
- The prefix of any `domain/folder` of a tenant, like `tenants.mydomain.com/tenant1`, as long as only one tenant is found.

The arguments `-as`, `-ss`, `-ds` and `-ts` act as wildcard for selecting a class of schemas as follows:

| Wildcard | Selected schemas                                                                |
| -------- | ------------------------------------------------------------------------------- |
| `-as`    | All schemas                                                                     |
| `-ss`    | Static schemas                                                                  |
| `-ds`    | Dynamic schemas                                                                 |
| `-ts`    | Tenant-like schemas: all dynamic schemas plus the reference schema if it exists |

It's possible to exclude schemas via the `-x` argument. This argument accepts the same inputs as `--schema`. Excluded schemas will take precedence over included ones.

At least one schema is mandatory. If it's not provided with the command, either explicitly or via wildcard params, it will be asked interactively, except when the option `--noinput` is passed, in which case the command will fail.

If `--parallel` is passed, the command will be run asynchronously, spawning multiple threads controlled by the setting `PGSCHEMAS_PARALLEL_MAX_PROCESSES`. This setting defaults to `None`, in which case the number of CPUs will be used.

By default, schemas that do not exist will be created (although migrations won't be applied). This can be bypassed by passing `--no-create-schemas`.

!!! Tip

    When in doubt of which schemas will be selected from a combination of arguments, we provide the management command `whowill` that can be used to just display the selected schemas.

### Inheritable commands

We also provide some base commands you can inherit, in order to mimic the behavior of `runschema`. By inheriting these you will get the arguments we discussed in the previous section. The base commands provide a `handle_schema` you must override in order to execute the actions you need on any given tenant.

The base commands are:

```python title="django_pgschemas/management/commands/__init__.py"
class SchemaCommand(WrappedSchemaOption, BaseCommand):

    def handle_schema(self, schema, *args, **options):
        """
        Extensible method to perform some action in a schema.
        """
        ...

class StaticSchemaCommand(SchemaCommand):
    """
    Management command that can only be run in static schemas.
    """
    ...

class DynamicSchemaCommand(SchemaCommand):
    """
    Management command that can only be run in dynamic schemas.
    """
    ...
```

!!! Warning

    Since these commands can work with the schemas of static and dynamic tenants, the parameter `schema` will be an instance of `django_pgschemas.schema.Schema`. Make sure to do the appropriate type checking before accessing the tenant members, as not always you will get an instance of the tenant model.
