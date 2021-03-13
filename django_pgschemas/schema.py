from django.db import connection


def get_current_schema():
    return connection._schema


def activate(schema):
    connection._set_schema(schema)


def deactivate():
    connection._set_schema_to_public()


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

    def get_primary_domain(self):
        """
        Returns the primary domain of the schema descriptor, if present.
        """

        class AdHocDomain:
            def __init__(self, domain, folder=None):
                self.domain = domain
                self.folder = folder
                self.is_primary = True

            def __str__(self):
                return "/".join([self.domain, self.folder]) if self.folder else self.domain

        return AdHocDomain(self.domain_url or self.schema_name, self.folder)
