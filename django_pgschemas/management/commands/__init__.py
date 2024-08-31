import enum

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Case, CharField, Q, Value, When
from django.db.models.functions import Concat
from django.db.utils import ProgrammingError

from django_pgschemas.management.commands._executors import parallel, sequential
from django_pgschemas.schema import Schema, get_current_schema
from django_pgschemas.utils import (
    create_schema,
    dynamic_models_exist,
    get_clone_reference,
    get_domain_model,
    get_tenant_model,
)


class CommandScope(enum.Enum):
    ALL = "all"
    DYNAMIC = "dynamic"
    STATIC = "static"

    @classmethod
    def allow_static(cls):
        return [cls.ALL, cls.STATIC]

    @classmethod
    def allow_dynamic(cls):
        return [cls.ALL, cls.DYNAMIC]


EXECUTORS = {
    "sequential": sequential,
    "parallel": parallel,
}


class WrappedSchemaOption:
    scope = CommandScope.ALL
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
            "-s",
            "--schema",
            nargs="+",
            dest="schemas",
            help="Schema(s) to execute the current command",
        )
        parser.add_argument(
            "-x",
            "--exclude-schema",
            nargs="+",
            dest="excluded_schemas",
            help="Schema(s) to exclude when executing the current command",
        )

        if self.allow_wildcards:
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
            "--parallel",
            dest="parallel",
            action="store_true",
            help="Run command in parallel mode",
        )
        parser.add_argument(
            "--no-create-schemas",
            dest="skip_schema_creation",
            action="store_true",
            help="Skip automatic creation of non-existing schemas",
        )

    def get_schemas_from_options(self, **options):
        skip_schema_creation = options.get("skip_schema_creation", False)
        try:
            schemas = self._get_schemas_from_options(**options)
        except ProgrammingError:
            # This happens with unmigrated database.
            # It can also happen when the tenant model contains unapplied migrations that break.
            raise CommandError(
                "Error while attempting to retrieve dynamic schemas. "
                "Perhaps you need to migrate the 'public' schema first?"
            )
        if self.specific_schemas is not None:
            schemas = [x for x in schemas if x in self.specific_schemas]
            if not schemas:
                raise CommandError("This command can only run in %s" % self.specific_schemas)
        if not skip_schema_creation:
            for schema in schemas:
                create_schema(schema, check_if_exists=True, sync_schema=False, verbosity=0)
        return schemas

    def get_executor_from_options(self, **options):
        return EXECUTORS["parallel"] if options.get("parallel") else EXECUTORS["sequential"]

    def get_scope_display(self):
        return "|".join(self.specific_schemas or []) or self.scope.value

    def _get_schemas_from_options(self, **options):
        schemas = options.get("schemas") or []
        excluded_schemas = options.get("excluded_schemas") or []
        include_all_schemas = options.get("all_schemas") or False
        include_static_schemas = options.get("static_schemas") or False
        include_dynamic_schemas = options.get("dynamic_schemas") or False
        include_tenant_schemas = options.get("tenant_schemas") or False
        dynamic_ready = dynamic_models_exist()
        allow_static = self.scope in CommandScope.allow_static()
        allow_dynamic = self.scope in CommandScope.allow_dynamic()
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
                    "Enter schema to run command (leave blank for running on '%s' schemas): "
                    % self.get_scope_display()
                ).strip()

                if schema:
                    schemas.append(schema)
                else:
                    include_all_schemas = True
            else:
                raise CommandError("No schema provided")

        TenantModel = get_tenant_model()
        has_domains = get_domain_model() is not None

        static_schemas = (
            [x for x in settings.TENANTS.keys() if x != "default"] if allow_static else []
        )
        dynamic_schemas = (
            TenantModel.objects.values_list("schema_name", flat=True)
            if TenantModel is not None and dynamic_ready and allow_dynamic
            else []
        )
        if clone_reference and allow_static:
            static_schemas.append(clone_reference)

        schemas_to_return = set()

        if include_all_schemas:
            if not allow_static and not allow_dynamic:
                raise CommandError("Including all schemas is NOT allowed")
            schemas_to_return = schemas_to_return.union(static_schemas + list(dynamic_schemas))
        if include_static_schemas:
            if not allow_static:
                raise CommandError("Including static schemas is NOT allowed")
            schemas_to_return = schemas_to_return.union(static_schemas)
        if include_dynamic_schemas:
            if not allow_dynamic:
                raise CommandError("Including dynamic schemas is NOT allowed")
            schemas_to_return = schemas_to_return.union(dynamic_schemas)
        if include_tenant_schemas:
            if not allow_dynamic:
                raise CommandError("Including tenant-like schemas is NOT allowed")
            schemas_to_return = schemas_to_return.union(dynamic_schemas)
            if clone_reference:
                schemas_to_return.add(clone_reference)

        def find_schema_by_reference(reference, as_excluded=False):
            if reference in settings.TENANTS and reference != "default" and allow_static:
                return reference
            elif reference == clone_reference:
                return reference
            elif (
                TenantModel is not None
                and dynamic_ready
                and TenantModel.objects.filter(schema_name=reference).exists()
                and allow_dynamic
            ):
                return reference
            else:
                local = []
                if allow_static:
                    local += [
                        schema_name
                        for schema_name, data in settings.TENANTS.items()
                        if schema_name not in ["public", "default"]
                        and any(x for x in data.get("DOMAINS", []) if x.startswith(reference))
                    ]
                if TenantModel is not None and dynamic_ready and allow_dynamic:
                    local += (
                        TenantModel.objects.annotate(
                            route=Case(
                                When(
                                    domains__folder="",
                                    then="domains__domain",
                                ),
                                default=Concat(
                                    "domains__domain",
                                    Value("/"),
                                    "domains__folder",
                                    output_field=CharField(),
                                ),
                                output_field=CharField(),
                            )
                            if has_domains
                            else Value("")
                        )
                        .filter(Q(schema_name=reference) | Q(route__startswith=reference))
                        .distinct()
                        .values_list("schema_name", flat=True)
                    )
                if not local:
                    message = (
                        "No schema found for '%s' (excluded)"
                        if as_excluded
                        else "No schema found for '%s'"
                    )
                    raise CommandError(message % reference)
                if len(local) > 1:
                    message = (
                        "More than one tenant found for schema '%s' by domain (excluded), "
                        "please, narrow down the filter"
                        if as_excluded
                        else "More than one tenant found for schema '%s' by domain, please, narrow down the filter"
                    )
                    raise CommandError(message % reference)
                return local[0]

        for schema in schemas:
            included = find_schema_by_reference(schema, as_excluded=False)
            schemas_to_return.add(included)

        for schema in excluded_schemas:
            excluded = find_schema_by_reference(schema, as_excluded=True)
            schemas_to_return -= {excluded}

        return (
            list(schemas_to_return)
            if "public" not in schemas_to_return
            else ["public"] + list(schemas_to_return - {"public"})
        )


class SchemaCommand(WrappedSchemaOption, BaseCommand):
    def handle(self, *args, **options):
        schemas = self.get_schemas_from_options(**options)
        executor = self.get_executor_from_options(**options)
        executor(schemas, self, "_raw_handle_schema", args, options, pass_schema_in_kwargs=True)

    def _raw_handle_schema(self, *args, **kwargs):
        kwargs.pop("schema_name")
        self.handle_schema(get_current_schema(), *args, **kwargs)

    def handle_schema(self, schema: Schema, *args, **options):
        raise NotImplementedError


class StaticSchemaCommand(SchemaCommand):
    scope = CommandScope.STATIC


class DynamicSchemaCommand(SchemaCommand):
    scope = CommandScope.DYNAMIC
