from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ._executors import sequential, parallel
from ...utils import get_tenant_model, create_schema

WILDCARD_ALL = ":all:"
WILDCARD_STATIC = ":static:"
WILDCARD_DYNAMIC = ":dynamic:"

EXECUTORS = {"sequential": sequential, "parallel": parallel}


class WrappedSchemaOption(object):
    allow_static = True
    allow_dynamic = True

    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            "--schema",
            nargs="?",
            dest="schema",
            default=WILDCARD_ALL,
            help="Schema to execute the current command",
        )
        parser.add_argument(
            "--executor",
            dest="executor",
            default="sequential",
            choices=EXECUTORS,
            help="Executor to be used for running command on schemas",
        )
        parser.add_argument(
            "--no-create-schemas",
            dest="skip_schema_creation",
            action="store_true",
            help="Skip automatic creation of non-existing schemas",
        )

    def get_schemas_from_options(self, **options):
        skip_schema_creation = options.get("skip_schema_creation", False)
        schemas = self._get_schemas_from_options(**options)
        if not skip_schema_creation:
            for schema in schemas:
                create_schema(schema, check_if_exists=True, sync_schema=False, verbosity=0)
        return schemas

    def get_executor_from_options(self, **options):
        return EXECUTORS[options.get("executor")]

    def _get_schemas_from_options(self, **options):
        schema = options.get("schema")

        if not schema:
            raise CommandError("No schema provided")

        TenantModel = get_tenant_model()
        static_schemas = [x for x in settings.TENANTS.keys() if x != "default"] if self.allow_static else []
        dynamic_schemas = TenantModel.objects.values_list("schema_name", flat=True) if self.allow_dynamic else []

        if schema == WILDCARD_ALL:
            if not self.allow_static and not self.allow_dynamic:
                raise CommandError("Schema wildcard %s is now allowed" % WILDCARD_ALL)
            return static_schemas + list(dynamic_schemas)
        elif schema == WILDCARD_STATIC:
            if not self.allow_static:
                raise CommandError("Schema wildcard %s is now allowed" % WILDCARD_STATIC)
            return static_schemas
        elif schema == WILDCARD_DYNAMIC:
            if not self.allow_dynamic:
                raise CommandError("Schema wildcard %s is now allowed" % WILDCARD_DYNAMIC)
            return list(dynamic_schemas)
        elif schema in settings.TENANTS and schema != "default" and self.allow_static:
            return [schema]
        elif TenantModel.objects.filter(schema_name=schema).exists() and self.allow_dynamic:
            return [schema]

        domain_matching_schemas = []

        if self.allow_static:
            domain_matching_schemas += [
                schema_name
                for schema_name, data in settings.TENANTS.items()
                if schema_name not in ["public", "default"]
                and any([x for x in data["DOMAINS"] if x.startswith(schema)])
            ]

        if self.allow_dynamic:
            domain_matching_schemas += (
                TenantModel.objects.filter(domains__domain__istartswith=schema)
                .distinct()
                .values_list("schema_name", flat=True)
            )

        if not domain_matching_schemas:
            raise CommandError("No tenant found for schema '%s'" % schema)
        if len(domain_matching_schemas) > 1:
            raise CommandError(
                "More than one tenant found for schema '%s' by domain, please, narrow down the filter" % schema
            )

        return domain_matching_schemas


class DynamicTenantCommand(WrappedSchemaOption, BaseCommand):
    allow_static = False
    allow_dynamic = True

    def handle(self, *args, **options):
        schemas = self.get_schemas_from_options(**options)
        executor = self.get_executor_from_options(**options)
        executor(schemas, type(self), "_raw_handle_tenant", args, options, pass_schema_in_kwargs=True)

    def _raw_handle_tenant(self, *args, **kwargs):
        TenantModel = get_tenant_model()
        schema_name = kwargs.pop("schema_name")
        tenant = TenantModel.objects.get(schema_name=schema_name)
        self.handle_tenant(tenant, *args, **kwargs)

    def handle_tenant(self, tenant, *args, **options):
        pass
