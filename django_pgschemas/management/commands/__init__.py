from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import CharField, Q, Value as V
from django.db.models.functions import Concat

from ._executors import sequential, parallel
from ...schema import SchemaDescriptor
from ...utils import get_tenant_model, dynamic_models_exist, create_schema, get_clone_reference

EXECUTORS = {"sequential": sequential, "parallel": parallel}


class WrappedSchemaOption(object):
    scope = "all"
    specific_schemas = None

    allow_interactive = True
    allow_wildcards = True

    def add_arguments(self, parser):
        if self.allow_interactive:
            parser.add_argument(
                "--noinput",
                "--no-input",
                action="store_false",
                dest="interactive",
                help="Tells Django to NOT prompt the user for input of any kind.",
            )
        parser.add_argument(
            "-s", "--schema", nargs="+", dest="schemas", help="Schema(s) to execute the current command"
        )
        parser.add_argument(
            "-as",
            "--include-all-schemas",
            action="store_true",
            dest="all_schemas",
            help="Include all schemas when executing the current command",
        )
        parser.add_argument(
            "-ss",
            "--include-static-schemas",
            action="store_true",
            dest="static_schemas",
            help="Include all static schemas when executing the current command",
        )
        parser.add_argument(
            "-ds",
            "--include-dynamic-schemas",
            action="store_true",
            dest="dynamic_schemas",
            help="Include all dynamic schemas when executing the current command",
        )
        parser.add_argument(
            "-ts",
            "--include-tenant-schemas",
            action="store_true",
            dest="tenant_schemas",
            help="Include all tenant-like schemas when executing the current command",
        )
        parser.add_argument(
            "-x",
            "--exclude-schema",
            nargs="+",
            dest="excluded_schemas",
            help="Schema(s) to exclude when executing the current command",
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
        if self.specific_schemas is not None:
            schemas = [x for x in schemas if x in self.specific_schemas]
            if not schemas:
                raise CommandError("This command can only run in %s" % self.specific_schemas)
        if not skip_schema_creation:
            for schema in schemas:
                create_schema(schema, check_if_exists=True, sync_schema=False, verbosity=0)
        return schemas

    def get_executor_from_options(self, **options):
        return EXECUTORS[options.get("executor")]

    def get_scope_display(self):
        return "|".join(self.specific_schemas or []) or self.scope

    def _get_schemas_from_options(self, **options):
        schemas = options.get("schemas") or []
        excluded_schemas = options.get("excluded_schemas") or []
        include_all_schemas = options.get("all_schemas") or False
        include_static_schemas = options.get("static_schemas") or False
        include_dynamic_schemas = options.get("dynamic_schemas") or False
        include_tenant_schemas = options.get("tenant_schemas") or False
        dynamic_ready = dynamic_models_exist()
        allow_static = self.scope in ["all", "static"]
        allow_dynamic = self.scope in ["all", "dynamic"]
        clone_reference = get_clone_reference()

        if (
            not schemas
            and not include_all_schemas
            and not include_static_schemas
            and not include_dynamic_schemas
            and not include_tenant_schemas
        ):
            if not self.allow_interactive:
                include_all_schemas = True
            elif options.get("interactive", True):
                schema = input(
                    "Enter schema to run command (leave blank for running on '%s' schemas): " % self.get_scope_display()
                ).strip()

                if schema:
                    schemas.append(schema)
                else:
                    include_all_schemas = True
            else:
                raise CommandError("No schema provided")

        TenantModel = get_tenant_model()
        static_schemas = [x for x in settings.TENANTS.keys() if x != "default"] if allow_static else []
        dynamic_schemas = (
            TenantModel.objects.values_list("schema_name", flat=True) if dynamic_ready and allow_dynamic else []
        )
        if clone_reference and allow_static:
            static_schemas.append(clone_reference)

        schemas_to_return = set()

        if include_all_schemas:
            if not self.allow_wildcards or (not allow_static and not allow_dynamic):
                raise CommandError("Including all schemas is now allowed")
            schemas_to_return = schemas_to_return.union(static_schemas + list(dynamic_schemas))
        if include_static_schemas:
            if not self.allow_wildcards or not allow_static:
                raise CommandError("Including static schemas is now allowed")
            schemas_to_return = schemas_to_return.union(static_schemas)
        if include_dynamic_schemas:
            if not self.allow_wildcards or not allow_dynamic:
                raise CommandError("Including dynamic schemas is now allowed")
            schemas_to_return = schemas_to_return.union(dynamic_schemas)
        if include_tenant_schemas:
            if not self.allow_wildcards or not allow_dynamic:
                raise CommandError("Including tenant-like schemas is now allowed")
            schemas_to_return = schemas_to_return.union(dynamic_schemas)
            if clone_reference:
                schemas_to_return.add(clone_reference)

        for schema in schemas:
            if schema in settings.TENANTS and schema != "default" and allow_static:
                schemas_to_return.add(schema)
            elif schema == clone_reference:
                schemas_to_return.add(schema)
            elif dynamic_ready and TenantModel.objects.filter(schema_name=schema).exists() and allow_dynamic:
                schemas_to_return.add(schema)

        schemas = list(set(schemas) - schemas_to_return)

        for schema in schemas:
            local = []
            if allow_static:
                local += [
                    schema_name
                    for schema_name, data in settings.TENANTS.items()
                    if schema_name not in ["public", "default"]
                    and any([x for x in data["DOMAINS"] if x.startswith(schema)])
                ]
            if dynamic_ready and allow_dynamic:
                local += (
                    TenantModel.objects.annotate(
                        route=Concat("domains__domain", V("/"), "domains__folder", output_field=CharField())
                    )
                    .filter(Q(domains__domain__istartswith=schema) | Q(route=schema))
                    .distinct()
                    .values_list("schema_name", flat=True)
                )
            if not local:
                raise CommandError("No schema found for '%s'" % schema)
            if len(local) > 1:
                raise CommandError(
                    "More than one tenant found for schema '%s' by domain, please, narrow down the filter" % schema
                )
            schemas_to_return.add(local.pop())

        excluded = []
        for schema in excluded_schemas:
            local = []
            if schema in ["public", clone_reference]:
                excluded.append(schema)
                continue
            local += [
                schema_name
                for schema_name, data in settings.TENANTS.items()
                if schema_name not in ["public", "default", clone_reference]
                and any([x for x in data["DOMAINS"] if x.startswith(schema)])
            ]
            local += (
                TenantModel.objects.annotate(
                    route=Concat("domains__domain", V("/"), "domains__folder", output_field=CharField())
                )
                .filter(Q(domains__domain__istartswith=schema) | Q(route=schema))
                .distinct()
                .values_list("schema_name", flat=True)
            )
            if not local:
                raise CommandError("No schema found for '%s' (excluded)" % schema)
            if len(local) > 1:
                raise CommandError(
                    "More than one tenant found for schema '%s' by domain (excluded), please, narrow down the filter"
                    % schema
                )
            excluded += local
        schemas_to_return -= set(excluded)

        return (
            list(schemas_to_return)
            if "public" not in schemas_to_return
            else ["public"] + list(schemas_to_return - {"public"})
        )


class TenantCommand(WrappedSchemaOption, BaseCommand):
    def handle(self, *args, **options):
        schemas = self.get_schemas_from_options(**options)
        executor = self.get_executor_from_options(**options)
        executor(schemas, type(self), "_raw_handle_tenant", args, options, pass_schema_in_kwargs=True)

    def _raw_handle_tenant(self, *args, **kwargs):
        schema_name = kwargs.pop("schema_name")
        if schema_name in settings.TENANTS:
            domains = settings.TENANTS[schema_name].get("DOMAINS", [])
            tenant = SchemaDescriptor.create(schema_name=schema_name, domain_url=domains[0] if domains else None)
            self.handle_tenant(tenant, *args, **kwargs)
        elif schema_name == get_clone_reference():
            tenant = SchemaDescriptor.create(schema_name=schema_name)
            self.handle_tenant(tenant, *args, **kwargs)
        else:
            TenantModel = get_tenant_model()
            tenant = TenantModel.objects.get(schema_name=schema_name)
            self.handle_tenant(tenant, *args, **kwargs)

    def handle_tenant(self, tenant, *args, **options):
        pass


class StaticTenantCommand(TenantCommand):
    scope = "static"


class DynamicTenantCommand(TenantCommand):
    scope = "dynamic"
