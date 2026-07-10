from django.core.management.base import BaseCommand

from notifications.providers import NullProvider, get_provider


class Command(BaseCommand):
    help = (
        "Send a one-off test email through the configured notification "
        "provider, to verify SMTP sending actually works end-to-end."
    )

    def add_arguments(self, parser):
        parser.add_argument("to", help="Recipient email address.")

    def handle(self, *args, **options):
        to = options["to"]
        provider = get_provider()

        if isinstance(provider, NullProvider):
            self.stdout.write(
                self.style.WARNING(
                    "No email provider is configured (EMAIL_HOST unset or "
                    f"DEMO_MODE=true) — this would be a no-op, not a real "
                    f"send to {to}. Set EMAIL_HOST/EMAIL_HOST_USER/"
                    "EMAIL_HOST_PASSWORD to test real sending."
                )
            )
            return

        provider.send(
            to=to,
            subject="Tryggare Moln test email",
            body="This is a test email confirming SMTP sending is configured correctly.",
        )
        self.stdout.write(self.style.SUCCESS(f"Sent test email to {to}."))
