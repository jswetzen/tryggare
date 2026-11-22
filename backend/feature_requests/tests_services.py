from django.contrib.auth.models import Permission
from django.test import TestCase

from accounts.models import AdminUser
from events import event_spec
from events.models import Event
from events.spec_test_support import at_now

from . import services
from .models import FeatureRequest, FeatureRequestComment
from .rules import FeatureRequestError

DATA = {
    "title": "Family price",
    "problem": "Families want one price for the group.",
    "desired": "A price for a group of attendees.",
    "touches": ["cap:family_groups", "code:registration_open"],
    "severity": "friction",
    "tried": ["Two tickets"],
    "workaround": {"used": "A discount code per family", "cost": "extra_steps"},
}


class ServiceCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = AdminUser.objects.create_superuser("owner", "pw12345")
        cls.coord = AdminUser.objects.create_user("coord", "pw12345")
        cls.coord.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="events", codename="change_event"
            )
        )
        cls.plain = AdminUser.objects.create_user("plain", "pw12345")
        with at_now():
            cls.event = event_spec.apply(event_spec.example_spec())[0]
        cls.second = Event.objects.create(
            name="Second", start_date="2027-08-01", end_date="2027-08-02"
        )


class PermissionTests(ServiceCase):
    def test_can_file_needs_event_change(self):
        self.assertTrue(services.can_file(self.coord))
        self.assertTrue(services.can_file(self.owner))
        self.assertFalse(services.can_file(self.plain))
        self.assertFalse(services.can_file(None))


class DraftTests(ServiceCase):
    def test_draft_is_stored_and_never_confirmed(self):
        row, match = services.file_draft(
            self.event, self.owner, DATA, source="assistant"
        )
        row.refresh_from_db()
        self.assertEqual(row.status, "draft")
        self.assertEqual(row.source, "assistant")
        self.assertEqual(row.dedupe_key, "cap:family_groups")
        self.assertEqual(row.validator, "existing")
        self.assertEqual(row.reach, "few_events")
        self.assertIsNone(match)
        self.assertIsNone(row.confirmed_by)
        self.assertEqual(row.filed_by, self.owner)
        self.assertEqual(row.event, self.event)

    def test_draft_reports_an_open_match(self):
        first, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        services.confirm(first, self.owner)
        _, match = services.file_draft(self.event, self.coord, DATA, source="organizer")
        self.assertEqual(match, {"id": first.public_id, "seen": 1})

    def test_serialize_has_no_local_fields(self):
        row, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        view = services.serialize(row)
        self.assertEqual(
            set(view),
            {
                "id",
                "title",
                "problem",
                "desired",
                "tried",
                "workaround",
                "brief_fragment",
                "touches",
                "severity",
                "matches_existing",
            },
        )

    def test_drafts_are_listed_per_user_and_event(self):
        mine, _ = services.file_draft(self.event, self.coord, DATA, source="organizer")
        services.file_draft(self.event, self.owner, DATA, source="assistant")
        services.file_draft(self.second, self.coord, DATA, source="organizer")
        self.assertEqual(list(services.drafts_for(self.event, self.coord)), [mine])

    def test_invalid_input_stores_nothing(self):
        with self.assertRaises(FeatureRequestError):
            services.file_draft(
                self.event,
                self.owner,
                {**DATA, "problem": "x@example.com"},
                "assistant",
            )
        self.assertFalse(FeatureRequest.objects.exists())


class ConfirmTests(ServiceCase):
    def test_confirm_without_match_records_who(self):
        row, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        row = services.confirm(row, self.coord)
        self.assertEqual((row.status, row.confirmed_by), ("confirmed", self.coord))

    def test_confirm_with_match_merges_and_keeps_text_as_comment(self):
        first, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        services.confirm(first, self.owner)
        second, _ = services.file_draft(
            self.second,
            self.coord,
            {
                **DATA,
                "desired": "One price for a family of any size.",
                "touches": ["cap:family_groups"],
            },
            source="organizer",
        )
        merged = services.confirm(second, self.coord)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(second.status, "duplicate")
        self.assertEqual(second.duplicate_of, first)
        self.assertEqual(first.status, "confirmed")
        self.assertEqual(first.seen, 2)
        self.assertEqual(first.reach, "some_events")
        self.assertEqual(merged.pk, first.pk)
        comment = FeatureRequestComment.objects.get(request=first)
        self.assertIn("One price for a family of any size.", comment.body)
        self.assertEqual(
            first.desired, DATA["desired"]
        )  # the original text is not merged into

    def test_evidence_is_appended_once(self):
        data = {**DATA, "touches": ["code:registration_open"]}
        first, _ = services.file_draft(self.event, self.owner, data, source="assistant")
        services.confirm(first, self.owner)
        second, _ = services.file_draft(
            self.second, self.coord, data, source="assistant"
        )
        services.confirm(second, self.coord)
        first.refresh_from_db()
        self.assertEqual(
            first.evidence,
            [{"kind": "validation_code", "ref": "code:registration_open"}],
        )

    def test_edits_run_the_checks_again_and_store_nothing_on_failure(self):
        row, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        with self.assertRaises(FeatureRequestError) as ctx:
            services.confirm(row, self.owner, {"problem": "Ask anna@example.com"})
        self.assertEqual(ctx.exception.errors[0]["code"], "personal_data")
        row.refresh_from_db()
        self.assertEqual((row.status, row.problem), ("draft", DATA["problem"]))

    def test_valid_edit_is_applied(self):
        row, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        row = services.confirm(row, self.owner, {"title": "Price for families"})
        self.assertEqual(row.title, "Price for families")
        self.assertEqual(row.status, "confirmed")

    def test_only_drafts_confirm(self):
        row, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        row = services.confirm(row, self.owner)
        with self.assertRaises(FeatureRequestError):
            services.confirm(row, self.owner)

    def test_a_second_click_on_a_stale_copy_does_not_merge_again(self):
        first, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        services.confirm(first, self.owner)
        second, _ = services.file_draft(
            self.second, self.coord, DATA, source="assistant"
        )
        stale = FeatureRequest.objects.get(pk=second.pk)
        services.confirm(second, self.coord)
        with self.assertRaises(FeatureRequestError) as ctx:
            services.confirm(stale, self.coord)
        self.assertEqual(ctx.exception.errors[0]["code"], "not_a_draft")
        first.refresh_from_db()
        self.assertEqual(first.seen, 2)
        self.assertEqual(FeatureRequestComment.objects.filter(request=first).count(), 1)

    def test_a_target_declined_since_it_was_read_is_refused(self):
        target, _ = services.file_draft(
            self.event, self.owner, DATA, source="assistant"
        )
        target = services.confirm(target, self.owner)
        FeatureRequest.objects.filter(pk=target.pk).update(status="declined")
        source, _ = services.file_draft(
            self.second, self.coord, DATA, source="assistant"
        )
        with self.assertRaises(FeatureRequestError):
            services.merge_into(source, target, self.owner)  # target is a stale copy
        source.refresh_from_db()
        self.assertEqual(source.status, "draft")

    def test_merge_target_must_be_open(self):
        target = FeatureRequest.objects.create(
            title="T",
            source="maintainer",
            problem="p",
            desired="d",
            touches=["cap:waitlists"],
            severity="friction",
            reach="few_events",
            validator="no",
            dedupe_key="cap:waitlists",
            status="declined",
        )
        source, _ = services.file_draft(
            self.event, self.owner, DATA, source="assistant"
        )
        with self.assertRaises(FeatureRequestError):
            services.merge_into(source, target, self.owner)

    def test_discard_only_drops_drafts(self):
        row, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        services.discard(row)
        self.assertFalse(FeatureRequest.objects.exists())
        kept, _ = services.file_draft(self.event, self.owner, DATA, source="assistant")
        kept = services.confirm(kept, self.owner)
        services.discard(kept)
        self.assertTrue(FeatureRequest.objects.filter(pk=kept.pk).exists())
