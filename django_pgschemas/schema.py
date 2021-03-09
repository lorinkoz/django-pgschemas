from asgiref.local import Local

_active = Local()


def get_current_schema():
    return getattr(_active, "value", None)


def set_schema_to_public():
    SchemaDescriptor.create(schema_name="public").activate()


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

    def activate(self):
        self.previous_schema = get_current_schema()
        self.ready = False  # Defines whether search path has been set
        _active.value = self

    def deactivate(self):
        previous_schema = getattr(self, "previous_schema", None)
        _active.value = previous_schema

    def __enter__(self):
        self.activate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deactivate()
