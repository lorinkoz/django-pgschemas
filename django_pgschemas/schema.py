from django.db import connection

from .signals import schema_activate


def get_current_schema():
    return connection._schema


def activate(schema):
    connection._set_schema(schema)
    schema_activate.send(sender=SchemaDescriptor, schema=schema)


def deactivate():
    connection._set_schema_to_public()
    schema_activate.send(sender=SchemaDescriptor, schema=SchemaDescriptor.create("public"))


activate_public = deactivate


class SchemaDescriptor:
    schema_name = None
    domain_url = None
    folder = None

    is_dynamic = False

    @staticmethod
    def create(schema_name, domain_url=None, folder=None):
        tenant = SchemaDescriptor()
        tenant.schema_name = schema_name
        tenant.domain_url = domain_url
        tenant.folder = folder
        return tenant

    def __enter__(self):
        self.previous_schema = connection._schema
        activate(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        previous_schema = getattr(self, "previous_schema", None)
        activate(previous_schema) if previous_schema else deactivate()
