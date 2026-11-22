"""Feature requests: what organizers and the assistant could not express. The record is
local; only a person copies one out (``export.py``). Plan: docs/roadmap/feature_requests.md."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

SOURCES = [
    ("organizer", _("Organizer")),
    ("assistant", _("Assistant")),
    ("validator", _("Validator warning")),
    ("trial", _("Trial")),
    ("eval", _("Eval")),
    ("maintainer", _("Maintainer")),
]
SEVERITIES = [
    ("blocks", _("Blocks the setup")),
    ("wrong_result", _("Wrong result")),
    ("risk", _("Risk of damage")),
    ("friction", _("Friction")),
    ("cosmetic", _("Cosmetic")),
]
REACHES = [
    ("most_events", _("Most events")),
    ("some_events", _("Some events")),
    ("few_events", _("Few events")),
]
LAYERS = [
    ("validator", _("Validator")),
    ("model", _("Model")),
    ("admin_ui", _("Admin UI")),
    ("public_form", _("Public form")),
    ("spec_example", _("Spec example")),
    ("docs", _("Docs")),
]
VALIDATORS = [
    ("existing", _("A check already flags it")),
    ("new_warning", _("A new warning could catch it")),
    ("no", _("Needs a model, UI or doc change")),
]
STATUSES = [
    ("draft", _("Draft")),
    ("confirmed", _("Confirmed")),
    ("triaged", _("Triaged")),
    ("planned", _("Planned")),
    ("done", _("Done")),
    ("declined", _("Declined")),
    ("duplicate", _("Duplicate")),
]
COSTS = [
    ("none", _("None")),
    ("extra_steps", _("Extra steps")),
    ("wrong_result", _("Wrong result")),
    ("not_possible", _("Not possible")),
]


class FeatureRequest(models.Model):
    """``public_id`` is ``FR-<pk>``: the pk is the database sequence, so ids are never reused."""

    OPEN_STATUSES = ("confirmed", "triaged", "planned")

    title = models.CharField(max_length=100, verbose_name=_("Title"))
    source = models.CharField(max_length=16, choices=SOURCES, verbose_name=_("Source"))
    problem = models.TextField(verbose_name=_("Problem"))
    tried = models.JSONField(default=list, blank=True, verbose_name=_("Tried"))
    # {"used": str, "cost": one of COSTS} or None when no workaround was built.
    workaround = models.JSONField(null=True, blank=True, verbose_name=_("Workaround"))
    desired = models.TextField(verbose_name=_("Desired"))
    touches = models.JSONField(default=list, verbose_name=_("Touches"))
    severity = models.CharField(
        max_length=16, choices=SEVERITIES, verbose_name=_("Severity")
    )
    reach = models.CharField(max_length=16, choices=REACHES, verbose_name=_("Reach"))
    layers = models.JSONField(default=list, blank=True, verbose_name=_("Layers"))
    validator = models.CharField(
        max_length=16, choices=VALIDATORS, verbose_name=_("Validator")
    )
    evidence = models.JSONField(default=list, blank=True, verbose_name=_("Evidence"))
    brief_fragment = models.CharField(
        max_length=300, null=True, blank=True, verbose_name=_("Brief fragment")
    )
    dedupe_key = models.CharField(
        max_length=200, db_index=True, verbose_name=_("Dedupe key")
    )
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
        verbose_name=_("Duplicate of"),
    )
    seen = models.PositiveIntegerField(default=1, verbose_name=_("Seen"))
    status = models.CharField(
        max_length=16,
        choices=STATUSES,
        default="draft",
        db_index=True,
        verbose_name=_("Status"),
    )

    # Local only: never in an export (feature_requests/export.py).
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feature_requests",
        verbose_name=_("Event"),
    )
    filed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Filed by"),
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Confirmed by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-pk"]
        verbose_name = _("Feature request")
        verbose_name_plural = _("Feature requests")

    def __str__(self) -> str:
        return f"{self.public_id} {self.title}"

    @property
    def public_id(self) -> str:
        return f"FR-{self.pk}"


class FeatureRequestComment(models.Model):
    """Free text from merged duplicates, kept for the maintainer and never exported."""

    request = models.ForeignKey(
        FeatureRequest,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Feature request"),
    )
    body = models.TextField(verbose_name=_("Comment"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Author"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["created_at", "pk"]
        verbose_name = _("Feature request comment")
        verbose_name_plural = _("Feature request comments")
