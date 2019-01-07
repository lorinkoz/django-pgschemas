from django.db import models

from django_pgschemas.models import TenantMixin, DomainMixin


class Tenant(TenantMixin):
    pass


class Domain(DomainMixin):
    pass
