from typing import Optional

from asgiref.local import Local

from .signals import schema_activate

_active = Local()


def get_default_schema() -> "SchemaDescriptor":
    return SchemaDescriptor.create("public")


def get_current_schema() -> "SchemaDescriptor":
    current_schema = getattr(_active, "value", None)
    return current_schema or get_default_schema()


def activate(schema: "SchemaDescriptor"):
    if not isinstance(schema, SchemaDescriptor):
        raise RuntimeError("'activate' must be called with a SchemaDescriptor descendant")

    _active.value = schema
    schema_activate.send(sender=SchemaDescriptor, schema=schema)


def deactivate():
    if hasattr(_active, "value"):
        del _active.value
    schema_activate.send(sender=SchemaDescriptor, schema=SchemaDescriptor.create("public"))


activate_public = deactivate


class SchemaDescriptor:
    schema_name = None
    domain_url = None
    folder = None

    is_dynamic = False

    @staticmethod
    def create(schema_name: str, domain_url: Optional[str] = None, folder: Optional[str] = None):
        schema = SchemaDescriptor()
        schema.schema_name = schema_name
        schema.domain_url = domain_url
        schema.folder = folder
        return schema

    def __enter__(self):
        self.previous_schema = get_current_schema()
        activate(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        previous_schema = getattr(self, "previous_schema", None)
        activate(previous_schema) if previous_schema else deactivate()
