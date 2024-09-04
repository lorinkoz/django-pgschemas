## Schema

Base representation of a Postgres schema.

```python

class Schema:
    schema_name: str
    routing: RoutingInfo = None

```

Routing contains information on the routing method used (e.g. domain, session, header). It's filled automatically via middleware but may be missing in other contexts (e.g. management commands).

### Routing info

Information on the routing method.

```python

class DomainInfo:
    domain: str
    folder: str | None = None

class SessionInfo:
    reference: str

class HeadersInfo:
    reference: str

RoutingInfo: TypeAlias = DomainInfo | SessionInfo | HeadersInfo | None

```

## Tenant model

Abstract base class for the tenant model.

```python

class TenantModel(Schema, models.Model):
    auto_create_schema = True
    auto_drop_schema = False

    schema_name = models.CharField(max_length=63, unique=True)

    class Meta:
        abstract = True

```

`auto_create_schema` controls whether a schema is automatically created when a instance of the tenant model is created. `auto_drop_schema` controls whether the schema is automatically deleted when the instance is deleted.

## Domain model

Abstract base class for the domain model. Optional when domain routing is not used.

```python

class DomainModel(models.Model):

    tenant = models.ForeignKey(
        settings.TENANTS["default"]["TENANT_MODEL"],
        db_index=True,
        related_name="domains",
        on_delete=models.CASCADE,
    )

    domain = models.CharField(max_length=253, db_index=True)
    folder = models.SlugField(max_length=253, blank=True, db_index=True)

    is_primary = models.BooleanField(default=True)
    redirect_to_primary = models.BooleanField(default=False)

    class Meta:
        abstract = True
        unique_together = ("domain", "folder")

```

There should only be one instance per tenant with `is_primary` set to `True`. If `redirect_to_primary` is `True` the routing middleware will perform a permanent redirect to whatever domain and folder is marked as primary.
