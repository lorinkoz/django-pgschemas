import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import connection


class TenantFileSystemStorage(FileSystemStorage):
    """
    Tenant aware file system storage. Appends the tenant identifier to the base
    location and base URL.
    """

    def get_schema_path_identifier(self):
        if not connection.schema:
            return ""
        path_identifier = connection.schema.schema_name
        if hasattr(connection.schema, "schema_pathname"):
            path_identifier = connection.schema.schema_pathname()
        elif hasattr(settings, "PGSCHEMAS_PATHNAME_FUNCTION"):
            path_identifier = settings.PGSCHEMAS_PATHNAME_FUNCTION(connection.schema)
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
        url_folder = self.get_schema_path_identifier()
        if url_folder and connection.schema and connection.schema.folder:
            # Since we're already prepending all URLs with schema, there is no
            # need to make the differentiation here
            url_folder = ""
        parent_base_url = super().base_url.strip("/")
        url = "/".join(["", parent_base_url, url_folder])
        if not url.endswith("/"):
            url += "/"
        return url
