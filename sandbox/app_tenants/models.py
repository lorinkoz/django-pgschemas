from django.contrib.auth import get_user_model
from django.db import models


class TenantData(models.Model):
    catalog = models.ForeignKey(
        "shared_public.Catalog", on_delete=models.CASCADE, related_name="tenant_objects"
    )
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="tenant_objects"
    )

    active = models.BooleanField(default=True)
