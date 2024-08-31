from typing import Any

from django.db.models.signals import pre_delete
from django.dispatch import Signal, receiver

from django_pgschemas.utils import get_tenant_model, schema_exists

schema_activate = Signal()
schema_activate.__doc__ = "Sent after a schema has been activated"

dynamic_tenant_needs_sync = Signal()
dynamic_tenant_needs_sync.__doc__ = (
    "Sent when a schema from a dynamic tenant needs to have migrations applied"
)

dynamic_tenant_post_sync = Signal()
dynamic_tenant_post_sync.__doc__ = (
    "Sent after a tenant has been saved, its schema created and all migrations applied"
)

dynamic_tenant_pre_drop = Signal()
dynamic_tenant_pre_drop.__doc__ = "Sent when a schema from a dynamic tenant is about to be dropped"


@receiver(pre_delete)
def tenant_delete_callback(sender: Any, instance: Any, **kwargs: object) -> None:
    TenantModel = get_tenant_model()
    if TenantModel is None:
        return
    if not isinstance(instance, TenantModel):
        return
    if instance.auto_drop_schema and schema_exists(instance.schema_name):
        dynamic_tenant_pre_drop.send(sender=TenantModel, tenant=instance.serializable_fields())
        instance.drop_schema()
