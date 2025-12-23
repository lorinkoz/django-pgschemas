from typing import Any

from django.core.checks import Tags, run_checks
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db.models import Model

from django_pgschemas.utils import clone_schema, get_domain_model, get_tenant_model


def strtobool(val: str) -> int:
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError(f"invalid truth value {val!r}")


class Command(BaseCommand):
    help = "Clones a schema"

    def _run_checks(self, **kwargs: Any) -> list[Any]:  # pragma: no cover
        issues = run_checks(tags=[Tags.database])
        issues.extend(super()._run_checks(**kwargs))
        return issues

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "source",
            help="The name of the schema you want to clone",
        )
        parser.add_argument(
            "destination",
            help="The name of the schema you want to create as clone",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Just show what clone would do; without actually cloning.",
        )

    def _ask(self, question: str) -> int:
        answer = None
        while answer is None:
            try:
                raw_answer = input(f"{question.strip()} [Y/n] ").strip() or "y"
                answer = strtobool(raw_answer)
            except ValueError:
                self.stderr.write(f"{raw_answer} is not a valid answer.")
                pass
        return answer

    def _check_required_field(self, field: Any, exclude: list[str] | None = None) -> bool:
        if exclude is None:
            exclude = []
        return (
            field.editable
            and not field.primary_key
            and not field.is_relation
            and not (
                field.null
                or field.has_default()
                or (field.blank and field.empty_strings_allowed)
                or getattr(field, "auto_now", False)
                or getattr(field, "auto_now_add", False)
            )
            and field.name not in exclude
        )

    def _get_constructed_instance(self, model_class: type[Model], data: dict[str, Any]) -> Model:
        fields = [
            field
            for field in model_class._meta.fields
            if self._check_required_field(field, list(data.keys()))
        ]
        instance = model_class(**data)
        if fields:
            self.stdout.write(
                self.style.WARNING(f"We need some data for model '{model_class._meta.model_name}':")
            )
            for field in fields:
                while field.name not in data:
                    raw_value = input(f"Value for field '{field.name}': ")
                    try:
                        data[field.name] = field.clean(raw_value, None)
                        instance = model_class(**data)
                        instance.clean()
                    except Exception as e:
                        if hasattr(e, "message"):
                            self.stderr.write(e.message)  # noqa
                        elif hasattr(e, "messages"):
                            self.stderr.write(" ".join(e.messages))  # noqa
                        else:
                            self.stderr.write(e)
                        data.pop(field.name, None)
        return instance

    def get_dynamic_tenant(self, **options: Any) -> tuple[Model | None, Model | None]:
        tenant = None
        domain = None
        if self._ask(
            "You are cloning a schema for a dynamic tenant. Would you like to create a database entry for it?"
        ):
            TenantModel = get_tenant_model()
            DomainModel = get_domain_model()
            if TenantModel is not None:
                tenant = self._get_constructed_instance(
                    TenantModel, {"schema_name": options["destination"]}
                )
            if DomainModel is not None:
                domain = self._get_constructed_instance(DomainModel, {"is_primary": True})
            if options["verbosity"] >= 1:
                self.stdout.write(self.style.WARNING("Looks good! Let's get to it!"))
        return tenant, domain

    def handle(self, *args: Any, **options: Any) -> None:
        tenant = None
        domain = None
        dry_run = options.get("dry_run")
        if options.get("interactive", True):
            TenantModel = get_tenant_model()
            if (
                TenantModel is not None
                and TenantModel.objects.filter(schema_name=options["source"]).exists()
            ):
                tenant, domain = self.get_dynamic_tenant(**options)
        try:
            clone_schema(options["source"], options["destination"], dry_run)
            if tenant and domain:
                if options["verbosity"] >= 1:
                    self.stdout.write("Schema cloned.")
                if not dry_run:
                    tenant.save()
                domain.tenant = tenant
                if not dry_run:
                    domain.save()
                if options["verbosity"] >= 1:
                    self.stdout.write("Tenant and domain successfully saved.")
            if options["verbosity"] >= 1:
                self.stdout.write("All done!")
        except Exception as e:
            if hasattr(e, "message"):
                raise CommandError(e.message)  # noqa
            elif hasattr(e, "messages"):
                raise CommandError(" ".join(e.messages))  # noqa
            else:
                raise CommandError(e)
