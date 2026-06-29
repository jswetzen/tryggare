"""
Aggregation for event/session report snapshots.

``build_event_report_data`` is a pure, read-only computation over live data; it
performs no writes and returns the JSON structure stored on
``EventReport.data``. ``generate_event_report`` builds and persists a snapshot.

All output is aggregate-only (no names, no per-child rows) so it is safe to keep
after the underlying PII is deleted. Staff are stored as display-name strings
because ``AdminUser`` rows are operational accounts, not the PII being purged.

Key definitions:
- unique_children: distinct children with >=1 check-in in the event's sessions.
- peak_concurrent: per session, the max number simultaneously checked in,
  computed by sweeping check-in/check-out times (an open record with no
  check-out is counted as still present).
- no-shows: holds a ticket but never checked in. Event level uses event passes;
  session level uses that session's session tickets.
- returning_families: families with >=1 check-in in a session of an *earlier*
  event (by start_date); new_families = the remaining participating families.
"""

from collections import defaultdict

from checkins.models import CheckInRecord
from events.models import EventTicket, SessionTicket
from families.models import Child, Family

SCHEMA_VERSION = 1

AGE_BUCKETS = ["0-2", "3-5", "6-8", "9-12", "13+", "unknown"]


def _age_on(birthdate, ref_date):
    """Age in whole years on ``ref_date``, or None if birthdate is missing."""
    if birthdate is None:
        return None
    return (
        ref_date.year
        - birthdate.year
        - ((ref_date.month, ref_date.day) < (birthdate.month, birthdate.day))
    )


def _age_bucket(age):
    if age is None or age < 0:
        return "unknown"
    if age <= 2:
        return "0-2"
    if age <= 5:
        return "3-5"
    if age <= 8:
        return "6-8"
    if age <= 12:
        return "9-12"
    return "13+"


def _peak_concurrent(records):
    """Max simultaneously-checked-in across the given records."""
    events = []
    for r in records:
        events.append((r.check_in_time, 1))
        if r.check_out_time is not None:
            events.append((r.check_out_time, -1))
    # At equal timestamps, process exits (-1) before entries (+1) so a
    # checkout/checkin swap at the same instant is not over-counted.
    events.sort(key=lambda e: (e[0], e[1]))
    peak = current = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def _avg_stay_minutes(records):
    """Average minutes between check-in and check-out for completed visits."""
    durations = [
        (r.check_out_time - r.check_in_time).total_seconds()
        for r in records
        if r.check_out_time is not None
    ]
    if not durations:
        return None
    return round(sum(durations) / len(durations) / 60, 1)


def _staff_name(staff):
    if staff is None:
        return "—"
    return staff.name or staff.username


def build_event_report_data(event) -> dict:
    """Compute the full snapshot for ``event`` from live data (no writes)."""
    sessions = list(event.sessions.all().order_by("start_time"))

    records = list(
        CheckInRecord.objects.filter(session__event=event).select_related(
            "child", "check_in_staff"
        )
    )

    event_child_ids = {r.child_id for r in records}
    unique_children = len(event_child_ids)
    total_checkins = len(records)

    # --- Ticketing / no-shows ---
    event_passes_issued = EventTicket.objects.filter(event=event).count()
    session_tickets_issued = SessionTicket.objects.filter(session__event=event).count()
    event_pass_child_ids = set(
        EventTicket.objects.filter(event=event).values_list("child_id", flat=True)
    )
    event_pass_no_shows = len(event_pass_child_ids - event_child_ids)

    # --- Demographics (event level), over children who actually checked in ---
    checked_in_children = Child.objects.filter(id__in=event_child_ids)
    age_buckets = {b: 0 for b in AGE_BUCKETS}
    with_allergies = 0
    for child in checked_in_children:
        age_buckets[_age_bucket(_age_on(child.birthdate, event.start_date))] += 1
        if child.allergies and child.allergies.strip():
            with_allergies += 1

    participating_family_ids = set(
        checked_in_children.values_list("family_id", flat=True)
    )
    returning_families = 0
    if participating_family_ids:
        returning_families = (
            Family.objects.filter(id__in=participating_family_ids)
            .filter(
                children__checkin_records__session__event__start_date__lt=event.start_date
            )
            .distinct()
            .count()
        )
    new_families = len(participating_family_ids) - returning_families

    # --- Operations (event level) ---
    labels_printed = sum(1 for r in records if r.label_printed)
    staff_counts = defaultdict(int)
    for r in records:
        staff_counts[_staff_name(r.check_in_staff)] += 1
    checkins_per_staff = sorted(
        ({"staff": name, "count": count} for name, count in staff_counts.items()),
        key=lambda row: (-row["count"], row["staff"]),
    )

    # --- Per-session breakdown ---
    records_by_session = defaultdict(list)
    for r in records:
        records_by_session[r.session_id].append(r)

    session_ticket_child_ids = defaultdict(set)
    for session_id, child_id in SessionTicket.objects.filter(
        session__event=event
    ).values_list("session_id", "child_id"):
        session_ticket_child_ids[session_id].add(child_id)

    sessions_data = []
    for s in sessions:
        s_records = records_by_session.get(s.id, [])
        s_child_ids = {r.child_id for r in s_records}
        s_ticket_child_ids = session_ticket_child_ids.get(s.id, set())
        sessions_data.append(
            {
                "name": s.name,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "unique_children": len(s_child_ids),
                "total_checkins": len(s_records),
                "peak_concurrent": _peak_concurrent(s_records),
                "supervised": sum(1 for r in s_records if r.supervised),
                "staffed_checkouts": sum(
                    1 for r in s_records if r.check_out_staff_id is not None
                ),
                "session_tickets_issued": len(s_ticket_child_ids),
                "session_ticket_no_shows": len(s_ticket_child_ids - s_child_ids),
                "labels_printed": sum(1 for r in s_records if r.label_printed),
                "avg_stay_minutes": _avg_stay_minutes(s_records),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "event": {
            "name": event.name,
            "start_date": event.start_date.isoformat(),
            "end_date": event.end_date.isoformat(),
            "session_count": len(sessions),
            "unique_children": unique_children,
            "total_checkins": total_checkins,
            "tickets": {
                "event_passes_issued": event_passes_issued,
                "session_tickets_issued": session_tickets_issued,
                "event_pass_no_shows": event_pass_no_shows,
            },
            "demographics": {
                "age_buckets": age_buckets,
                "with_allergies": with_allergies,
                "returning_families": returning_families,
                "new_families": new_families,
            },
            "operations": {
                "labels_printed": labels_printed,
                "checkins_per_staff": checkins_per_staff,
                "avg_stay_minutes": _avg_stay_minutes(records),
            },
        },
        "sessions": sessions_data,
    }


def generate_event_report(event, user=None):
    """Build and persist an :class:`~reports.models.EventReport` for ``event``."""
    from .models import EventReport

    data = build_event_report_data(event)
    return EventReport.objects.create(
        event=event,
        event_name=event.name,
        event_start_date=event.start_date,
        event_end_date=event.end_date,
        generated_by=user,
        unique_children=data["event"]["unique_children"],
        total_checkins=data["event"]["total_checkins"],
        data=data,
    )
