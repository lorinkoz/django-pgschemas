import os

from django.core.files.storage import FileSystemStorage

from django_pgschemas.routing.info import DomainInfo
from django_pgschemas.schema import get_current_schema
from django_pgschemas.settings import get_pathname_function


class TenantFileSystemStorage(FileSystemStorage):
    """
    Tenant aware file system storage. Appends the tenant identifier to the base
    location and base URL.
    """

    def get_schema_path_identifier(self):
        schema = get_current_schema()

        if schema is None:
            return ""

        path_identifier = schema.schema_name

        if hasattr(schema, "schema_pathname"):
            path_identifier = schema.schema_pathname()

        elif pathname_function := get_pathname_function():
            path_identifier = pathname_function(schema)

        return path_identifier

    @property  # To avoid caching of tenant
    def base_location(self):
        """
        Appends base location with the schema path identifier.
        """
        file_folder = self.get_schema_path_identifier()
        location = os.path.join(super().base_location, file_folder)

        if not location.endswith("/"):
            location += "/"

        return location

    @property  # To avoid caching of tenant
    def location(self):
        return super().location

    @property  # To avoid caching of tenant
    def base_url(self):
        """
        Optionally appends base URL with the schema path identifier.
        If the current schema is already using a folder, no path identifier is
        appended.
        """
        schema = get_current_schema()
        url_folder = self.get_schema_path_identifier()

        # Specific case of domain+folder routing
        if (
            url_folder
            and schema
            and isinstance(schema.routing, DomainInfo)
            and schema.routing.folder
        ):
            # Since we're already prepending all URLs with schema, there is no
            # need to make the differentiation here
            url_folder = ""

        parent_base_url = super().base_url.strip("/")
        url = "/".join(["", parent_base_url, url_folder])

        if not url.endswith("/"):
            url += "/"

        return url
