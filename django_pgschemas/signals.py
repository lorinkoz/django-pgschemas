from django.db.models.signals import pre_delete
from django.dispatch import Signal, receiver

from .utils import get_tenant_model, schema_exists

schema_post_sync = Signal(providing_args=["tenant"])
schema_post_sync.__doc__ = "Sent after a tenant has been saved, its schema created and synced"

schema_needs_sync = Signal(providing_args=["tenant"])
schema_needs_sync.__doc__ = "Sent when a schema needs to be synced"

schema_pre_drop = Signal(providing_args=["tenant"])
schema_pre_drop.__doc__ = "Sent when a schema is about to be dropped"


@receiver(pre_delete)
def tenant_delete_callback(sender, instance, **kwargs):
    if not isinstance(instance, get_tenant_model()):
        return
    if instance.auto_drop_schema and schema_exists(instance.schema_name):
        schema_pre_drop.send(sender=get_tenant_model(), tenant=instance.serializable_fields())
        instance.drop_schema()
