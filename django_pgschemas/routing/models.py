from django.conf import settings
from django.db import models, transaction

from django_pgschemas.models import TenantModel
from django_pgschemas.utils import get_domain_model


class DomainModel(models.Model):
    """
    All models that store the domains must inherit this class.
    """

    tenant = (
        models.ForeignKey(
            settings.TENANTS["default"]["TENANT_MODEL"],
            db_index=True,
            related_name="domains",
            on_delete=models.CASCADE,
        )
        if getattr(settings, "TENANTS", {}).get("default")
        else None
    )

    domain = models.CharField(max_length=253, db_index=True)
    folder = models.SlugField(max_length=253, blank=True, db_index=True)

    is_primary = models.BooleanField(default=True)
    redirect_to_primary = models.BooleanField(default=False)

    class Meta:
        abstract = True
        unique_together = (("domain", "folder"),)

    def __str__(self) -> str:
        return "/".join([self.domain, self.folder]) if self.folder else self.domain

    @transaction.atomic
    def save(self, *args: object, **kwargs: object) -> None:
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

    def absolute_url(self, path: str) -> str:
        """
        Constructs an absolute url for this domain / folder and a given path
        """
        parts = [self.domain]

        if self.folder:
            parts.append(self.folder)

        parts.append(path)

        final_path = "/".join(parts).replace("//", "/")

        return f"//{final_path}"


def get_primary_domain_for_tenant(tenant: TenantModel) -> DomainModel | None:
    DomainModel = get_domain_model()

    if DomainModel is None:
        return None

    try:
        return tenant.domains.get(is_primary=True)
    except DomainModel.DoesNotExist:
        return None
