from enum import Flag

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ._executors import sequential, parallel
from ...utils import get_tenant_model, create_schema
from ...volatile import VolatileTenant

WILDCARD_ALL = ":all:"
WILDCARD_STATIC = ":static:"
WILDCARD_DYNAMIC = ":dynamic:"

EXECUTORS = {"sequential": sequential, "parallel": parallel}


class SchemaScope(Flag):
    STATIC = 1
    DYNAMIC = 2
    ALL = 3


class WrappedSchemaOption(object):
    interactive = True
    scope = SchemaScope.ALL

    def add_arguments(self, parser):
        parser.add_argument("-s", "--schema", dest="schema", help="Schema to execute the current command")
        if self.interactive:
            parser.add_argument(
                "--noinput",
                "--no-input",
                action="store_false",
                dest="interactive",
                help="Tells Django to NOT prompt the user for input of any kind.",
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
        schema = options.get("schema", "")
        allow_static = self.scope & SchemaScope.STATIC
        allow_dynamic = self.scope & SchemaScope.DYNAMIC

        if not schema:
            if not self.interactive:
                schema = WILDCARD_ALL
            elif options["interactive"]:
                schema = input(
                    "Enter schema to run command (leave blank for running on '%s' schemas): " % self.scope.name
                ).strip()
                if not schema:
                    schema = WILDCARD_ALL
            else:
                raise CommandError("No schema provided")

        TenantModel = get_tenant_model()
        static_schemas = [x for x in settings.TENANTS.keys() if x != "default"] if allow_static else []
        dynamic_schemas = TenantModel.objects.values_list("schema_name", flat=True) if allow_dynamic else []

        if schema == WILDCARD_ALL:
            if not allow_static and not allow_dynamic:
                raise CommandError("Schema wildcard %s is now allowed" % WILDCARD_ALL)
            return static_schemas + list(dynamic_schemas)
        elif schema == WILDCARD_STATIC:
            if not allow_static:
                raise CommandError("Schema wildcard %s is now allowed" % WILDCARD_STATIC)
            return static_schemas
        elif schema == WILDCARD_DYNAMIC:
            if not allow_dynamic:
                raise CommandError("Schema wildcard %s is now allowed" % WILDCARD_DYNAMIC)
            return list(dynamic_schemas)
        elif schema in settings.TENANTS and schema != "default" and allow_static:
            return [schema]
        elif TenantModel.objects.filter(schema_name=schema).exists() and allow_dynamic:
            return [schema]

        domain_matching_schemas = []

        if allow_static:
            domain_matching_schemas += [
                schema_name
                for schema_name, data in settings.TENANTS.items()
                if schema_name not in ["public", "default"]
                and any([x for x in data["DOMAINS"] if x.startswith(schema)])
            ]

        if allow_dynamic:
            domain_matching_schemas += (
                TenantModel.objects.filter(domains__domain__istartswith=schema)
                .distinct()
                .values_list("schema_name", flat=True)
            )

        if not domain_matching_schemas:
            raise CommandError("No schema found for '%s'" % schema)
        if len(domain_matching_schemas) > 1:
            raise CommandError(
                "More than one tenant found for schema '%s' by domain, please, narrow down the filter" % schema
            )

        return domain_matching_schemas


class TenantCommand(WrappedSchemaOption, BaseCommand):
    def handle(self, *args, **options):
        schemas = self.get_schemas_from_options(**options)
        executor = self.get_executor_from_options(**options)
        executor(schemas, type(self), "_raw_handle_tenant", args, options, pass_schema_in_kwargs=True)

    def _raw_handle_tenant(self, *args, **kwargs):
        schema_name = kwargs.pop("schema_name")
        if schema_name in settings.TENANTS:
            domains = settings.TENANTS[schema_name].get("DOMAINS", [])
            tenant = VolatileTenant.create(schema_name=schema_name, domain_url=domains[0] if domains else None)
            self.handle_tenant(tenant, *args, **kwargs)
        else:
            TenantModel = get_tenant_model()
            tenant = TenantModel.objects.get(schema_name=schema_name)
            self.handle_tenant(tenant, *args, **kwargs)

    def handle_tenant(self, tenant, *args, **options):
        pass


class StaticTenantCommand(TenantCommand):
    scope = SchemaScope.STATIC


class DynamicTenantCommand(TenantCommand):
    scope = SchemaScope.DYNAMIC
