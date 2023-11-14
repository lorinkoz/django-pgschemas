import logging
from typing import Any

from django_pgschemas.routing.info import DomainInfo
from django_pgschemas.schema import get_current_schema


class SchemaContextFilter(logging.Filter):
    """
    Add the current routing info to log records.
    """

    def filter(self, record: Any) -> bool:
        current_schema = get_current_schema()
        record.schema_name = current_schema.schema_name

        match current_schema.routing:
            case DomainInfo(domain, folder):
                record.domain = domain
                record.folder = folder
            case _:
                pass
        return True
