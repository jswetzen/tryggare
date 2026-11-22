from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from assistant.pii import free_text_kind

from . import export, services
from .models import FeatureRequest, FeatureRequestComment, LAYERS
from .rules import touch_problem


class LayerFilter(admin.SimpleListFilter):
    """``layers`` is a JSON list, so this filters in Python (a small local table)."""

    title = _("layer")
    parameter_name = "layer"

    def lookups(self, request, model_admin):
        return LAYERS

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(pk__in=[r.pk for r in queryset if value in r.layers])


class CommentInline(admin.TabularInline):
    """Read-only: comments come from merges, which ran the personal-data check."""

    model = FeatureRequestComment
    extra = 0
    can_delete = False
    fields = ("body", "author", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class FeatureRequestAdminForm(forms.ModelForm):
    class Meta:
        model = FeatureRequest
        fields = [
            "title",
            "status",
            "severity",
            "problem",
            "desired",
            "tried",
            "workaround",
            "touches",
            "brief_fragment",
            "dedupe_key",
            "duplicate_of",
            "layers",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Merge targets: open requests that are not duplicates themselves, and not this one.
        rows = FeatureRequest.objects.filter(
            status__in=FeatureRequest.OPEN_STATUSES, duplicate_of__isnull=True
        )
        if self.instance.pk:
            rows = rows.exclude(pk=self.instance.pk)
        self.fields["duplicate_of"].queryset = rows

    def clean(self):
        data = super().clean()
        for name in ("title", "problem", "desired", "brief_fragment"):
            value = data.get(name)
            if value and (kind := free_text_kind(value)):
                self.add_error(
                    name, f"Looks like {kind}. Describe the shape, not a person."
                )
        for i, item in enumerate(data.get("tried") or []):
            if isinstance(item, str) and (kind := free_text_kind(item)):
                self.add_error("tried", f"Item {i + 1} looks like {kind}.")
        used = (data.get("workaround") or {}).get("used")
        if used and (kind := free_text_kind(used)):
            self.add_error("workaround", f"The workaround looks like {kind}.")
        for term in data.get("touches") or []:
            if (why := touch_problem(term)) is not None:
                self.add_error("touches", f"A term {why}.")
        if data.get("status") == "duplicate" and not data.get("duplicate_of"):
            self.add_error("duplicate_of", _("Choose the request this one duplicates."))
        return data


@admin.register(FeatureRequest)
class FeatureRequestAdmin(admin.ModelAdmin):
    form = FeatureRequestAdminForm
    change_list_template = "feature_requests/change_list.html"
    list_display = (
        "public_id",
        "title",
        "status",
        "severity",
        "source",
        "reach",
        "seen",
        "dedupe_key",
    )
    list_filter = ("status", "severity", "source", LayerFilter)
    search_fields = ("title", "dedupe_key")
    readonly_fields = (
        "public_id",
        "source",
        "reach",
        "validator",
        "evidence",
        "seen",
        "event",
        "filed_by",
        "confirmed_by",
        "created_at",
    )
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "public_id",
                    "title",
                    "status",
                    "severity",
                    "reach",
                    "validator",
                ]
            },
        ),
        (
            _("The need"),
            {"fields": ["problem", "desired", "tried", "workaround", "brief_fragment"]},
        ),
        (
            _("Triage"),
            {
                "fields": [
                    "touches",
                    "layers",
                    "dedupe_key",
                    "duplicate_of",
                    "seen",
                    "evidence",
                ]
            },
        ),
        (
            _("Local only, never exported"),
            {"fields": ["source", "event", "filed_by", "confirmed_by", "created_at"]},
        ),
    ]
    inlines = [CommentInline]
    actions = [
        "mark_triaged",
        "mark_planned",
        "mark_done",
        "mark_declined",
        "copy_as_github_issue",
    ]

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path(
                "<path:object_id>/github-issue/",
                self.admin_site.admin_view(self.github_issue_view),
                name="%s_%s_github_issue" % info,
            ),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        # Counts by key over requests someone may act on; drafts and merged duplicates are not counted.
        counts = (
            FeatureRequest.objects.exclude(status__in=("draft", "duplicate"))
            .values("dedupe_key")
            .annotate(requests=Count("pk"), seen_total=Sum("seen"))
            .order_by("-seen_total", "dedupe_key")[:50]
        )
        return super().changelist_view(
            request, {**(extra_context or {}), "counts": counts}
        )

    def has_add_permission(self, request):
        # Requests come from organizers, the assistant or a trial, through the review
        # flow; the admin form does not carry the fields a new one needs.
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Choosing a target is a merge (seen, evidence, comment) on top of the save.
        if change and "duplicate_of" in form.changed_data and obj.duplicate_of_id:
            services.merge_into(obj, obj.duplicate_of, by=request.user)

    def _bulk_status(self, request, queryset, status):
        # Drafts are the organizer's until confirmed; merged duplicates keep their status.
        updated = queryset.exclude(status__in=("draft", "duplicate")).update(
            status=status
        )
        self.message_user(request, f"{updated} request(s) set to {status}.")

    @admin.action(description=_("Set status to triaged"))
    def mark_triaged(self, request, queryset):
        self._bulk_status(request, queryset, "triaged")

    @admin.action(description=_("Set status to planned"))
    def mark_planned(self, request, queryset):
        self._bulk_status(request, queryset, "planned")

    @admin.action(description=_("Set status to done"))
    def mark_done(self, request, queryset):
        self._bulk_status(request, queryset, "done")

    @admin.action(description=_("Set status to declined"))
    def mark_declined(self, request, queryset):
        self._bulk_status(request, queryset, "declined")

    @admin.action(description=_("Copy as GitHub issue (one request)"))
    def copy_as_github_issue(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, _("Select exactly one request."), level="error")
            return None
        url = reverse(
            "admin:%s_%s_github_issue"
            % (self.model._meta.app_label, self.model._meta.model_name),
            args=[queryset.get().pk],
        )
        return HttpResponseRedirect(url)

    def github_issue_view(self, request, object_id):
        if not self.has_view_permission(request):
            raise PermissionDenied
        fr = get_object_or_404(FeatureRequest, pk=object_id)
        return render(
            request,
            "feature_requests/copy_issue.html",
            {
                **self.admin_site.each_context(request),
                "fr": fr,
                "issue": export.render(fr),
                "opts": self.model._meta,
            },
        )
