from threading import local


_active = local()


class ActiveSchemaHandler:
    def get_active_schema(self):
        return getattr(_active, "value", None)

    def set_active_schema(self, schema):
        _active.value = schema

    active = property(get_active_schema, set_active_schema)

    def set_schema(self, schema_descriptor):
        """
        Main API method to set current schema.
        """
        assert isinstance(
            schema_descriptor, SchemaDescriptor
        ), "'set_schema' must be called with a SchemaDescriptor descendant"
        schema_descriptor.ready = False  # Defines whether search path has been set
        self.set_active_schema(schema_descriptor)

    def set_schema_to(self, schema_name, domain_url=None, folder=None):
        self.set_schema(SchemaDescriptor.create(schema_name, domain_url, folder))

    def set_schema_to_public(self):
        """
        Instructs to stay in the 'public' schema.
        """
        self.set_schema_to("public")


schema_handler = ActiveSchemaHandler()


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
        self.previous_schema = schema_handler.active
        schema_handler.set_schema(self)

    def deactivate(self):
        """
        Syntax sugar to return to previous schema or public

        Usage:
            some_schema_descriptor.deactivate()
        """
        previous_schema = getattr(self, "previous_schema", None)
        schema_handler.set_schema(previous_schema) if previous_schema else schema_handler.set_schema_to_public()

    @staticmethod
    def deactivate_all():
        """
        Syntax sugar to return to public schema

        Usage:
            SchemaDescriptor.deactivate_all()
        """
        schema_handler.set_schema_to_public()

    def __enter__(self):
        self.activate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deactivate()

    def get_primary_domain(self):
        """
        Returns the primary domain of the schema descriptor, if present.
        """
        if self.domain_url:
            return "/".join([self.domain_url, self.folder]) if self.folder else self.domain_url
        return None
