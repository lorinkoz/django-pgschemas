from django.db import models

from django_pgschemas.models import DomainMixin, TenantMixin


class Tenant(TenantMixin):
    pass


class Domain(DomainMixin):
    pass


class Catalog(models.Model):
    pass
