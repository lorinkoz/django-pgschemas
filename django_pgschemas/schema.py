from django.db import connection


class SchemaDescriptor(object):
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

    def activate(self):
        """
        Syntax sugar that helps with fast tenant changing

        Usage:
            some_schema_descriptor.activate()
        """
        self.previous_schema = connection.schema
        connection.set_schema(self)

    def deactivate(self):
        """
        Syntax sugar to return to previous schema or public

        Usage:
            some_schema_descriptor.deactivate()
        """
        previous_schema = getattr(self, "previous_schema", None)
        connection.set_schema(previous_schema) if previous_schema else connection.set_schema_to_public()

    @staticmethod
    def deactivate_all():
        """
        Syntax sugar to return to public schema

        Usage:
            SchemaDescriptor.deactivate_all()
        """
        connection.set_schema_to_public()

    def __enter__(self):
        self.activate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deactivate()

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
