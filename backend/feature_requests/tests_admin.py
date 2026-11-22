from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AdminUser
from events import event_spec
from events.spec_test_support import at_now

from . import export
from .admin import FeatureRequestAdminForm
from .models import FeatureRequest, FeatureRequestComment

PLAIN_STATICFILES = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)


def make(
    title="Family price",
    key="cap:family_groups",
    status="confirmed",
    event=None,
    **extra,
):
    return FeatureRequest.objects.create(
        title=title,
        source="assistant",
        problem="Families want one price.",
        desired="One price for a group.",
        tried=["Two tickets"],
        workaround={"used": "A code per family", "cost": "extra_steps"},
        touches=[key],
        severity="friction",
        reach="few_events",
        layers=["model"],
        validator="no",
        evidence=[],
        dedupe_key=key,
        status=status,
        event=event,
        **extra,
    )


@PLAIN_STATICFILES
class AdminCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = AdminUser.objects.create_superuser("fradmin", "pw12345")
        with at_now():
            cls.event = event_spec.apply(event_spec.example_spec())[0]

    def setUp(self):
        self.client.force_login(self.admin)


class ExportTests(AdminCase):
    def test_export_has_no_local_only_fields(self):
        row = make(event=self.event, filed_by=self.admin, confirmed_by=self.admin)
        FeatureRequestComment.objects.create(
            request=row, body="Private note about Kalle", author=self.admin
        )
        issue = export.render(row)
        text = issue["title"] + issue["body"] + (issue["url"] or "")
        self.assertNotIn(self.event.name, text)
        self.assertNotIn("fradmin", text)
        self.assertNotIn("Private note", text)
        self.assertNotIn(row.created_at.isoformat()[:10], text)
        self.assertNotIn(row.public_id, text)

    def test_sections_follow_the_issue_template(self):
        body = export.render(make())["body"]
        for heading in (
            "## Problem description / use case",
            "## Proposed solution",
            "## Alternatives considered",
            "## Is this for a specific church or event type?",
            "## Additional context",
        ):
            self.assertIn(heading, body)
        self.assertIn("A code per family (cost: extra_steps)", body)

    def test_prefilled_link_points_at_the_issue_form_with_key_label(self):
        url = export.render(make())["url"]
        parts = urlsplit(url)
        self.assertEqual(
            f"{parts.scheme}://{parts.netloc}{parts.path}",
            "https://github.com/jswetzen/tryggare/issues/new",
        )
        query = parse_qs(parts.query)
        self.assertEqual(query["labels"], ["enhancement,fr:cap:family_groups"])
        self.assertTrue(query["title"][0].startswith("[Feature] "))

    def test_a_link_too_long_is_omitted_not_cut(self):
        row = make(title="Ö" * 100)
        row.problem = "ö" * 600
        row.desired = "ö" * 600
        row.tried = ["ö" * 300] * 5
        self.assertIsNone(export.render(row)["url"])


class AdminPageTests(AdminCase):
    def test_changelist_filters_by_status_and_layer(self):
        make(title="Confirmed one", status="confirmed")
        make(title="Triaged one", key="new:other", status="triaged")
        url = reverse("admin:feature_requests_featurerequest_changelist")
        page = self.client.get(url, {"status__exact": "triaged"})
        self.assertContains(page, "Triaged one")
        self.assertNotContains(page, "Confirmed one")
        page = self.client.get(url, {"layer": "docs"})
        self.assertNotContains(page, "Confirmed one")

    def test_counts_by_key_sum_seen_and_skip_drafts(self):
        make(title="A", key="cap:family_groups", status="confirmed", seen=3)
        make(title="B", key="cap:family_groups", status="triaged", seen=2)
        make(title="Draft", key="cap:draft_only", status="draft")
        page = self.client.get(
            reverse("admin:feature_requests_featurerequest_changelist")
        )
        counts = {row["dedupe_key"]: row for row in page.context["counts"]}
        self.assertEqual(counts["cap:family_groups"]["seen_total"], 5)
        self.assertNotIn("cap:draft_only", counts)

    def test_bulk_status_leaves_drafts_alone(self):
        draft = make(title="Draft", key="cap:x", status="draft")
        open_one = make(title="Open", key="cap:y", status="confirmed")
        url = reverse("admin:feature_requests_featurerequest_changelist")
        self.client.post(
            url, {"action": "mark_done", "_selected_action": [draft.pk, open_one.pk]}
        )
        draft.refresh_from_db()
        open_one.refresh_from_db()
        self.assertEqual((draft.status, open_one.status), ("draft", "done"))

    def test_copy_action_needs_exactly_one_request(self):
        one = make(title="One", key="cap:one")
        two = make(title="Two", key="cap:two")
        url = reverse("admin:feature_requests_featurerequest_changelist")
        response = self.client.post(
            url, {"action": "copy_as_github_issue", "_selected_action": [one.pk]}
        )
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response["Location"])
        self.assertContains(page, "https://github.com/jswetzen/tryggare/issues/new")
        self.assertContains(page, "[Feature] One")
        response = self.client.post(
            url,
            {"action": "copy_as_github_issue", "_selected_action": [one.pk, two.pk]},
        )
        self.assertNotIn(
            "github-issue", response.get("Location", "")
        )  # back to the list, with a message

    def test_copy_page_needs_view_permission(self):
        row = make()
        staff = AdminUser.objects.create_user("noview", "pw12345", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(
            reverse("admin:feature_requests_featurerequest_github_issue", args=[row.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_copy_page_for_a_user_with_view(self):
        row = make()
        staff = AdminUser.objects.create_user("viewer", "pw12345", is_staff=True)
        staff.user_permissions.add(
            Permission.objects.get(codename="view_featurerequest")
        )
        self.client.force_login(staff)
        response = self.client.get(
            reverse("admin:feature_requests_featurerequest_github_issue", args=[row.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_an_unconfirmed_draft_cannot_be_exported(self):
        row = make(status="draft")
        response = self.client.get(
            reverse("admin:feature_requests_featurerequest_github_issue", args=[row.pk])
        )
        self.assertEqual(response.status_code, 404)


class AdminFormTests(AdminCase):
    def data(self, **changes):
        base = {
            "title": "Family price",
            "status": "confirmed",
            "severity": "friction",
            "problem": "Families want one price.",
            "desired": "One price for a group.",
            "tried": "[]",
            "workaround": "null",
            "touches": '["cap:family_groups"]',
            "brief_fragment": "",
            "dedupe_key": "cap:family_groups",
            "duplicate_of": "",
            "layers": '["model"]',
        }
        base.update(changes)
        return base

    def test_change_page_renders_and_add_is_closed(self):
        row = make(event=self.event)
        page = self.client.get(
            reverse("admin:feature_requests_featurerequest_change", args=[row.pk])
        )
        self.assertContains(page, "FR-%d" % row.pk)
        self.assertEqual(
            self.client.get(
                reverse("admin:feature_requests_featurerequest_add")
            ).status_code,
            403,
        )

    def test_personal_data_in_free_text_is_refused(self):
        form = FeatureRequestAdminForm(data=self.data(problem="Mail anna@example.com"))
        self.assertFalse(form.is_valid())
        self.assertIn("problem", form.errors)
        self.assertNotIn("anna@", str(form.errors))

    def test_unknown_touch_term_is_refused(self):
        form = FeatureRequestAdminForm(data=self.data(touches='["cap:not_real"]'))
        self.assertFalse(form.is_valid())
        self.assertIn("touches", form.errors)

    def test_personal_data_in_touches_and_key_is_refused(self):
        form = FeatureRequestAdminForm(
            data=self.data(touches='["new:p1203021234"]', dedupe_key="new:p1203021234")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("touches", form.errors)
        self.assertIn("dedupe_key", form.errors)
        self.assertNotIn("1203021234", str(form.errors))

    def test_json_fields_must_have_their_shape(self):
        for name, value in [
            ("tried", '"one text"'),
            ("tried", "[1]"),
            ("workaround", '["used"]'),
            ("workaround", '{"used": "x"}'),
            ("workaround", '{"used": "x", "cost": "free"}'),
            ("touches", '"cap:family_groups"'),
            ("layers", '[{"a": 1}]'),
            ("layers", '["nowhere"]'),
        ]:
            with self.subTest(name=name, value=value):
                form = FeatureRequestAdminForm(data=self.data(**{name: value}))
                self.assertFalse(form.is_valid())
                self.assertIn(name, form.errors)
        ok = self.data(
            workaround='{"used": "An extra for all", "cost": "wrong_result"}'
        )
        self.assertTrue(FeatureRequestAdminForm(data=ok).is_valid())

    def test_duplicate_status_needs_a_target(self):
        form = FeatureRequestAdminForm(data=self.data(status="duplicate"))
        self.assertFalse(form.is_valid())
        self.assertIn("duplicate_of", form.errors)

    def test_choosing_a_target_merges_on_save(self):
        target = make(
            title="Target", key="cap:family_groups", status="confirmed", seen=1
        )
        source = make(
            title="Source",
            key="cap:family_groups",
            status="confirmed",
            event=self.event,
        )
        self.client.post(
            reverse("admin:feature_requests_featurerequest_change", args=[source.pk]),
            {
                "title": "Edited title",
                "status": "confirmed",
                "severity": "friction",
                "problem": source.problem,
                "desired": source.desired,
                "tried": "[]",
                "workaround": "null",
                "touches": '["cap:family_groups"]',
                "brief_fragment": "",
                "dedupe_key": "cap:family_groups",
                "duplicate_of": target.pk,
                "layers": '["model"]',
                # The read-only comments inline still posts its management form.
                "comments-TOTAL_FORMS": "0",
                "comments-INITIAL_FORMS": "0",
                "comments-MIN_NUM_FORMS": "0",
                "comments-MAX_NUM_FORMS": "1000",
            },
        )
        source.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual((source.status, source.duplicate_of), ("duplicate", target))
        self.assertEqual(
            source.title, "Edited title"
        )  # other edits in the same save survive
        self.assertEqual(target.seen, 2)
        self.assertEqual(
            FeatureRequestComment.objects.filter(request=target).count(), 1
        )
