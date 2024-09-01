from django.db import models

from django_pgschemas.postgresql.base import check_schema_name
from django_pgschemas.schema import Schema
from django_pgschemas.signals import (
    dynamic_tenant_needs_sync,
    dynamic_tenant_post_sync,
    dynamic_tenant_pre_drop,
)
from django_pgschemas.utils import (
    create_or_clone_schema,
    drop_schema,
    schema_exists,
)


class TenantModel(Schema, models.Model):
    """
    All tenant models must inherit this class.
    """

    auto_create_schema = True
    """
    Set this flag to `False` on a parent class if you don't want the schema
    to be automatically created upon save.
    """

    auto_drop_schema = False
    """
    *USE THIS WITH CAUTION!*
    Set this flag to `True` on a parent class if you want the schema to be
    automatically deleted if the tenant row gets deleted.
    """

    is_dynamic = True
    """
    Leave this as `True`. Denotes it's a database controlled tenant.
    """

    schema_name = models.CharField(max_length=63, unique=True, validators=[check_schema_name])

    class Meta:
        abstract = True

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: list[str] | None = None,
        verbosity: int = 1,
    ) -> None:
        is_new = self.pk is None

        super().save(force_insert, force_update, using, update_fields)

        if is_new and self.auto_create_schema:
            try:
                self.create_schema(verbosity=verbosity)
                dynamic_tenant_post_sync.send(sender=TenantModel, tenant=self.serializable_fields())
            except Exception:
                # We failed creating the tenant, delete what we created and re-raise the exception
                self.delete(force_drop=True)
                raise
        elif is_new:
            # Although we are not using the schema functions directly, the signal might be registered by a listener
            dynamic_tenant_needs_sync.send(sender=TenantModel, tenant=self.serializable_fields())
        elif not is_new and self.auto_create_schema and not schema_exists(self.schema_name):
            # Create schemas for existing models, deleting only the schema on failure
            try:
                self.create_schema(verbosity=verbosity)
                dynamic_tenant_post_sync.send(sender=TenantModel, tenant=self.serializable_fields())
            except Exception:
                # We failed creating the schema, delete what we created and re-raise the exception
                self.drop_schema()
                raise

    def delete(
        self, using: str | None = None, keep_parents: bool = False, force_drop: bool = False
    ) -> None:
        """
        Deletes this row. Drops the tenant's schema if the attribute
        `auto_drop_schema` is `True`.
        """
        if force_drop or self.auto_drop_schema:
            dynamic_tenant_pre_drop.send(sender=TenantModel, tenant=self.serializable_fields())
            self.drop_schema()

        super().delete(using, keep_parents)

    def serializable_fields(self) -> "TenantModel":
        """
        In certain cases the model isn't serializable so you may want to only
        send the id.
        """
        return self

    def create_schema(self, sync_schema: bool = True, verbosity: int = 1) -> bool:
        """
        Creates or clones the schema `schema_name` for this tenant.
        """
        return create_or_clone_schema(self.schema_name, sync_schema, verbosity)

    def drop_schema(self) -> bool:
        """
        Drops the schema.
        """
        return drop_schema(self.schema_name)
