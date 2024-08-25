from django.conf import settings
from django.db import models

from django_pgschemas.models import TenantModel
from django_pgschemas.routing.models import DomainModel


class Tenant(TenantModel):
    pass


if settings.TENANTS.get("default", {}).get("DOMAIN_MODEL", None) is not None:

    class Domain(DomainModel):
        pass


class Catalog(models.Model):
    pass
