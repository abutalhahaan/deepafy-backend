from django.core.management.base import BaseCommand, CommandError

from institution.models import Subject


class Command(BaseCommand):
    help = "Create a global Deepafy subject."

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)
        parser.add_argument(
            "code",
            type=str,
            nargs="?",
            default="",
        )

    def handle(self, *args, **options):
        name = options["name"].strip()
        code = options["code"].strip()

        if not name:
            raise CommandError("Subject name is required.")

        existing = Subject.objects.filter(
            name__iexact=name,
        ).first()

        if existing:
            raise CommandError(
                f"Subject already exists: {existing.name} (ID: {existing.id})"
            )

        subject = Subject.objects.create(
            name=name,
            code=code,
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Subject created: {subject.id} | {subject.name} | {subject.code}"
            )
        )
