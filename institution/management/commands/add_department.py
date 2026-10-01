from django.core.management.base import BaseCommand, CommandError

from institution.models import Department


class Command(BaseCommand):
    help = "Create a global Deepafy department."

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)
        parser.add_argument("code", type=str, nargs="?", default="")

    def handle(self, *args, **options):
        name = options["name"].strip()
        code = options["code"].strip()

        if not name:
            raise CommandError("Department name is required.")

        existing = Department.objects.filter(name__iexact=name).first()

        if existing:
            raise CommandError(
                f"Department already exists: {existing.name} (ID: {existing.id})"
            )

        department = Department.objects.create(
            name=name,
            code=code,
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Department created: "
                f"{department.id} | {department.name} | {department.code}"
            )
        )
