from django.db import models

from django_pgschemas.models import TenantModel
from django_pgschemas.routing.models import DomainModel


class Tenant(TenantModel):
    pass


class Domain(DomainModel):
    pass


class Catalog(models.Model):
    pass
