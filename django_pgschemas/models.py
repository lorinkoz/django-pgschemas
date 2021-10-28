from django.conf import settings
from django.db import models, transaction

from .postgresql_backend.base import check_schema_name
from .schema import SchemaDescriptor
from .signals import dynamic_tenant_needs_sync, dynamic_tenant_post_sync, dynamic_tenant_pre_drop
from .utils import create_or_clone_schema, drop_schema, get_domain_model, schema_exists


class TenantMixin(SchemaDescriptor, models.Model):
    """
    All tenant models must inherit this class.
    """

    auto_create_schema = True
    """
    Set this flag to ``False`` on a parent class if you don't want the schema
    to be automatically created upon save.
    """

    auto_drop_schema = False
    """
    **USE THIS WITH CAUTION!**
    Set this flag to ``True`` on a parent class if you want the schema to be
    automatically deleted if the tenant row gets deleted.
    """

    is_dynamic = True
    """
    Leave this as ``True``. Denotes it's a database controlled tenant.
    """

    schema_name = models.CharField(max_length=63, unique=True, validators=[check_schema_name])

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        verbosity = kwargs.pop("verbosity", 1)
        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new and self.auto_create_schema:
            try:
                self.create_schema(verbosity=verbosity)
                dynamic_tenant_post_sync.send(sender=TenantMixin, tenant=self.serializable_fields())
            except Exception:
                # We failed creating the tenant, delete what we created and re-raise the exception
                self.delete(force_drop=True)
                raise
        elif is_new:
            # Although we are not using the schema functions directly, the signal might be registered by a listener
            dynamic_tenant_needs_sync.send(sender=TenantMixin, tenant=self.serializable_fields())
        elif not is_new and self.auto_create_schema and not schema_exists(self.schema_name):
            # Create schemas for existing models, deleting only the schema on failure
            try:
                self.create_schema(verbosity=verbosity)
                dynamic_tenant_post_sync.send(sender=TenantMixin, tenant=self.serializable_fields())
            except Exception:
                # We failed creating the schema, delete what we created and re-raise the exception
                self.drop_schema()
                raise

    def delete(self, force_drop=False, *args, **kwargs):
        """
        Deletes this row. Drops the tenant's schema if the attribute
        ``auto_drop_schema`` is ``True``.
        """
        if force_drop or self.auto_drop_schema:
            dynamic_tenant_pre_drop.send(sender=TenantMixin, tenant=self.serializable_fields())
            self.drop_schema()
        super().delete(*args, **kwargs)

    def serializable_fields(self):
        """
        In certain cases the user model isn't serializable so you may want to
        only send the id.
        """
        return self

    def create_schema(self, sync_schema=True, verbosity=1):
        """
        Creates or clones the schema ``schema_name`` for this tenant.
        """
        return create_or_clone_schema(self.schema_name, sync_schema, verbosity)

    def drop_schema(self):
        """
        Drops the schema.
        """
        return drop_schema(self.schema_name)

    def get_primary_domain(self):
        try:
            domain = self.domains.get(is_primary=True)
            return domain
        except get_domain_model().DoesNotExist:
            return None


class DomainMixin(models.Model):
    """
    All models that store the domains must inherit this class.
    """

    tenant = models.ForeignKey(
        settings.TENANTS["default"]["TENANT_MODEL"], db_index=True, related_name="domains", on_delete=models.CASCADE
    )

    domain = models.CharField(max_length=253, db_index=True)
    folder = models.SlugField(max_length=253, blank=True, db_index=True)

    is_primary = models.BooleanField(default=True)
    redirect_to_primary = models.BooleanField(default=False)

    class Meta:
        abstract = True
        unique_together = (("domain", "folder"),)

    def __str__(self):
        return "/".join([self.domain, self.folder]) if self.folder else self.domain

    @transaction.atomic
    def save(self, *args, **kwargs):
        using = kwargs.get("using")
        domain_list = self.__class__.objects
        if using:
            domain_list = domain_list.using(using)
        domain_list = domain_list.filter(tenant=self.tenant, is_primary=True).exclude(pk=self.pk)
        self.is_primary = self.is_primary or (not domain_list.exists())
        if self.is_primary:
            domain_list.update(is_primary=False)
            if self.redirect_to_primary:
                self.redirect_to_primary = False
        super().save(*args, **kwargs)

    def absolute_url(self, path):
        """
        Constructs an absolute url for this domain / folder and a given path
        """
        folder = self.folder and "/" + self.folder
        if not path.startswith("/"):
            path = "/" + path
        return "//" + self.domain + folder + path
