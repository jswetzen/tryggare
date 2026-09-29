<script lang="ts">
  /**
   * Public self-serve event registration form.
   *
   * Parallel to the existing public /qr/[token] route: unauthenticated,
   * no persistent guardian account. On submit, the backend materializes
   * Family/Parent/Child rows immediately (status=pending_verification) and
   * emails a one-time verification link — see /register/verify/[token].
   *
   * Phase 3: when the event has active TicketTypes configured, each
   * attendee picks one and can attach per-attendee Extras; the booking can
   * also carry per-registration Extras (e.g. a shared cabin). Events with
   * no TicketTypes configured keep the original flat-price behavior
   * unchanged (see backend registrations/pricing.py::calculate_total).
   */
  import { onMount } from 'svelte';
  import { t, locale } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { registrationApi } from '$lib/api/registrationService';
  import { extractErrorMessage, extractFieldError, type ApiError } from '$lib/api/client';
  import type {
    PromoCodeValidation,
    RegistrationEventInfo,
    RegistrationExtraInfo,
    RegistrationExtraSelectionPayload,
    RegistrationSubmitPayload,
    RegistrationTicketType
  } from '$lib/api/types';
  import ConsentCapture, { type HealthInfoStatus } from '$lib/components/checkin/ConsentCapture.svelte';
  import EyebrowLabel from '$lib/components/ui/EyebrowLabel.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Alert from '$lib/components/ui/Alert.svelte';
  import { isValidPhone } from '$lib/utils/phone';

  type HealthConsentStatus = 'not_applicable' | 'granted' | 'declined';

  interface ExtraSelectionState {
    selected: boolean;
    choiceId: string;
    quantity: number;
  }

  interface ParentRow {
    first_name: string;
    last_name: string;
    phone: string;
    email: string;
    relationship_type: string;
    allergies: string;
    notes: string;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
    ticketTypeId: string;
    // True from the moment a promo-code removal (see handleRemovePromoCode)
    // clears this row's ticketTypeId because it was holding a now-retracted
    // unlocked type — drives the "Koden togs bort" caption on this row's
    // select. Cleared the instant the row picks a ticket again (see
    // handleParentTicketTypeChange/handleChildTicketTypeChange), not on any
    // other interaction — the point is "this selection changed out from
    // under you," which stops being true only once a new pick is made.
    promoReset: boolean;
    extraSelections: Record<string, ExtraSelectionState>;
  }

  interface ChildRow {
    first_name: string;
    last_name: string;
    birthdate: string;
    // True when the browser's own validity check on the date input
    // (rangeUnderflow/rangeOverflow against the min/max this page already
    // sets) says the current value isn't submittable — e.g. a digit-by-digit
    // typo like "0001-02-02", or a future date. Read straight off
    // input.validity on change, never re-derived with a custom parser. While
    // true, the birthdate is treated as "not really entered yet": no age
    // prose, no ticket-eligibility warning, so a bad date never masquerades
    // as a ticket problem.
    birthdateRangeInvalid: boolean;
    allergies: string;
    notes: string;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
    ticketTypeId: string;
    // See ParentRow.promoReset above — same purpose, same clearing rule.
    promoReset: boolean;
    extraSelections: Record<string, ExtraSelectionState>;
  }

  // One line in the top-of-form error summary (increment 5, 2026-09-28) —
  // built fresh on every blocked submit attempt (client-side validation) or
  // failed POST (server-side field errors, see submitPayload's catch
  // block). `focusSelector` is a CSS selector for the control this problem
  // is about, resolved with document.querySelector at click time rather
  // than held as a live element ref — the fields this points at are inside
  // #each blocks keyed by array index, so a stable ref per field would mean
  // a ref array kept in sync with parents/children, which is more
  // machinery than a selector lookup buys here. null means the problem
  // isn't about one specific control (e.g. "add at least one parent or
  // child") and renders as plain text rather than a button.
  interface SubmitProblem {
    id: string;
    message: string;
    focusSelector: string | null;
  }

  // Client-side format check only (R2, registration dev-cycle round 4,
  // increment 5 revision) — novalidate (see the form's own comment below)
  // removed the browser's built-in type="email" format check along with
  // its premature validation-bubble popup, so this is now the only thing
  // that catches "missing @" / "missing domain" before the round trip.
  // Deliberately simple, not a full RFC 5322 validator: the backend's own
  // EmailField is still the real gate (see contactEmailServerError below
  // for its 400 folded into this same banner item).
  const EMAIL_FORMAT_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const eventId = $derived($page.params.eventId ?? '');
  // Staff preview: ?preview=1 bypasses the "not open yet" landing screen so
  // staff can walk through the real form before announcing it, but never
  // bypasses the server-side window check — see submit_registration's
  // registration_window_status gate, the actual enforcement point.
  const isPreview = $derived($page.url.searchParams.get('preview') === '1');

  function formatDateTime(iso: string): string {
    // Follow the page's own sv/en toggle rather than the browser's OS
    // locale, so the date doesn't clash with the surrounding Swedish (or
    // English) copy.
    const localeTag = $locale === 'sv' ? 'sv-SE' : 'en-GB';
    return new Date(iso).toLocaleString(localeTag, {
      dateStyle: 'long',
      timeStyle: 'short'
    });
  }

  function formatDateRange(startIso: string, endIso: string): string {
    const localeTag = $locale === 'sv' ? 'sv-SE' : 'en-GB';
    const start = new Date(startIso).toLocaleDateString(localeTag, { dateStyle: 'long' });
    if (startIso === endIso) return start;
    const end = new Date(endIso).toLocaleDateString(localeTag, { dateStyle: 'long' });
    return `${start} – ${end}`;
  }

  function formatCurrency(amount: number | string): string {
    // Follow the page's own sv/en toggle (see formatDateTime above) rather
    // than the browser's OS locale, so the decimal separator matches the
    // surrounding Swedish (comma) or English (period) copy.
    const value = typeof amount === 'string' ? parseFloat(amount) : amount;
    const localeTag = $locale === 'sv' ? 'sv-SE' : 'en-GB';
    return value.toLocaleString(localeTag, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // A transposed-but-valid date (2021-03-12 entered as 2021-12-03) is
  // otherwise accepted silently by the native picker and nobody notices —
  // native mm/dd vs dd/mm picker order isn't actually the bug (a real
  // Swedish browser renders it in Swedish order), but a word month is
  // unambiguous in *any* locale, so echoing the parsed date back as prose
  // lets the guardian catch a transposition themselves. Age is computed as
  // of the event's start date (not today) since that's the age that
  // actually matters for ticket age-band eligibility.
  function ageAt(birthdateIso: string, asOfIso: string): number {
    const b = new Date(`${birthdateIso}T00:00:00`);
    const asOf = new Date(`${asOfIso}T00:00:00`);
    let age = asOf.getFullYear() - b.getFullYear();
    const hadBirthdayThisYear =
      asOf.getMonth() > b.getMonth() ||
      (asOf.getMonth() === b.getMonth() && asOf.getDate() >= b.getDate());
    if (!hadBirthdayThisYear) age -= 1;
    return age;
  }

  function birthdateProse(birthdateIso: string): string {
    if (!birthdateIso) return '';
    const parsed = new Date(`${birthdateIso}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return '';
    const localeTag = $locale === 'sv' ? 'sv-SE' : 'en-GB';
    const dateStr = parsed.toLocaleDateString(localeTag, {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
    const asOfIso = eventInfo?.start_date ?? todayIso;
    const age = ageAt(birthdateIso, asOfIso);
    return $t('register.birthdateProse', { values: { date: dateStr, age } });
  }

  // Bounds for the birthdate <input type="date">: never a future date, and
  // never more than 120 years back (a plausible outer bound for anyone
  // attending with a parent/guardian). `max`/`min` alone don't fix the
  // locale-format confusion below, but they do stop an obviously-wrong
  // typo (e.g. a transposed year) from being submittable at all.
  const todayIso = new Date().toISOString().slice(0, 10);
  const minBirthdateIso = (() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 120);
    return d.toISOString().slice(0, 10);
  })();

  function emptyParent(): ParentRow {
    return {
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      // No default — 2026-09-24 owner decision: the parent must actively
      // choose, rather than silently inheriting "Annat"/"Other". See
      // relationshipMissing/handleSubmit's own check below for the
      // enforcement, and register.relationshipPlaceholder for the select's
      // unchosen state.
      relationship_type: '',
      allergies: '',
      notes: '',
      healthInfoStatus: 'none',
      consentNoticeShared: false,
      ticketTypeId: '',
      promoReset: false,
      extraSelections: {}
    };
  }

  function emptyChild(): ChildRow {
    return {
      first_name: '',
      last_name: '',
      birthdate: '',
      birthdateRangeInvalid: false,
      allergies: '',
      notes: '',
      healthInfoStatus: 'none',
      consentNoticeShared: false,
      ticketTypeId: '',
      promoReset: false,
      extraSelections: {}
    };
  }

  let eventInfo = $state<RegistrationEventInfo | null>(null);
  let loadingEvent = $state(true);
  let eventNotFound = $state(false);

  let familyName = $state('');
  let contactEmail = $state('');
  let parents = $state<ParentRow[]>([emptyParent()]);
  let children = $state<ChildRow[]>([emptyChild()]);
  // Per-registration extras (e.g. a shared cabin) — one selection state per
  // Extra, not per person.
  let registrationExtraSelections = $state<Record<string, ExtraSelectionState>>({});
  // Honeypot: hidden from real users via CSS. Bots that fill every field
  // trip it; the backend responds as if successful but persists nothing.
  let website = $state('');

  // Promo code: an explicit "apply" click (not auto-validated on every
  // keystroke) queries validate_promo_code for a preview — never locks or
  // reserves the code, just tells the form what to show. The real,
  // authoritative redemption happens again from scratch server-side at
  // submission (see _resolve_promo_code); this can still fail there if
  // the code's last slot was claimed in between.
  let promoCode = $state('');
  let promoCodeValidation = $state<PromoCodeValidation | null>(null);
  let promoCodeChecking = $state(false);
  let promoCodeError = $state('');
  // The exact trimmed text `promoCodeValidation` was validated against —
  // compared at submit time (see the guard in handleSubmit) so a guardian
  // can't submit whatever is currently typed in the box on the strength of
  // an *earlier* code's validation. In practice this rarely diverges from
  // "promoCodeValidation is non-null", since the on:input handler below
  // already nulls promoCodeValidation on every keystroke — this exists for
  // clarity at the comparison site, not because the two can drift apart.
  let promoCodeAppliedValue = $state('');
  // is_hidden ticket types merged into eventInfo.ticket_types by the last
  // successful checkPromoCode (see its own comment) — tracked so
  // retractPromoUnlockedTicketTypes below knows exactly which entries to
  // remove again, and which attendee selections referencing them are now
  // dangling, when the code that unlocked them is edited away or cleared.
  let promoCodeUnlockedIds = $state<string[]>([]);
  // Set by handleRemovePromoCode ("Ta bort") when a code is explicitly
  // un-applied — an aria-live line under the field naming what just changed
  // (registration dev-cycle round 4, increment 3 revision, R2). Distinct
  // from promoCodeError: this is neutral status, not a rejection.
  let promoRemovalMessage = $state('');

  let error = $state('');
  // The raw DRF error body from a failed submit, e.g.
  // {"children": {"1": ["..."]}} for a per-attendee ticket-type failure
  // (see registrations/views.py::submit_registration). Drives the inline
  // per-attendee errors below; `error` above carries the banner text.
  let errorDetails = $state<unknown>(null);
  let errorBannerEl = $state<HTMLElement | null>(null);
  // The named, itemized breakdown that drives the error banner's list
  // (increment 5, 2026-09-28) — one entry per missing/invalid thing, each
  // naming the attendee it's about where there is one. Populated two ways:
  // handleSubmit's own client-side checks below (accumulated rather than
  // stopping at the first problem, so a parent who's missing both the
  // contact email and a child's Boende choice sees both at once), and
  // submitPayload's catch block for a 400 whose body maps to a specific
  // parent/child index (see extractFieldError). `error` above still carries
  // a single top line — the generic heading when these are client-side
  // problems, or the server's own message text when it isn't attributable
  // to a specific attendee (e.g. a flat "ticket_type" sold-out error) — the
  // two render together in the same banner, see the template below.
  let submitProblems = $state<SubmitProblem[]>([]);
  let submitting = $state(false);
  let submitted = $state(false);
  let referenceCode = $state<string | null>(null);
  // Replayed by the confirmation screen's "resend" action — see
  // handleSubmit's payload comment for why this is a plain resubmit rather
  // than a dedicated resend endpoint.
  let lastSubmitPayload = $state<RegistrationSubmitPayload | null>(null);
  let resending = $state(false);
  let resendStatus = $state<'sent' | 'error' | null>(null);
  // False when the server stored the registration but couldn't send the
  // confirmation email — the guardian is told plainly rather than being sent
  // to watch an inbox nothing is coming to.
  let emailSent = $state(true);

  // Set only when a submit's response body carries `code:
  // "registration_already_pending"` — the backend's (event, contact_email)
  // dedup was hit and this submission's form data was silently discarded in
  // favor of the still-pending registration (2026-09-28 incident: a parent
  // used "Edit and resend" to add a forgotten child, saw the ordinary
  // success screen, and the child was never saved — see
  // registrations/views.py::_execute_submit_registration's comment on this
  // branch). null means "no pending-duplicate state"; renders a dedicated
  // screen instead of the normal success screen so this is visible rather
  // than silent. `emailResent` is true only when the backend actually sent
  // a fresh token just now (response.email_sent === true) — the cooldown
  // branch omits email_sent entirely, which must NOT read as "a new email
  // went out."
  let pendingDuplicate = $state<{ referenceCode: string | null; emailResent: boolean } | null>(
    null
  );

  // Idempotency key for the primary submit — generated once here, at
  // module-eval time (page mount), not inside handleSubmit, specifically so
  // a network failure or a double submit that slips past `submitting`'s
  // guard sends the *same* key on every retry of this one attempt. Added
  // 2026-09-24: an audit of this flow found nothing stopping a retried POST
  // from materializing a second Family/Parent/Child/EventTicket set or
  // sending a second verification email — see backend
  // registrations/models.py::RegistrationIdempotencyKey for the full
  // mechanism this key drives. Reset only in handleEditEmail below, the one
  // point in this flow where the guardian is deliberately starting a fresh
  // submission (e.g. correcting the contact email) rather than retrying the
  // one that just happened — reusing the old key there would make the
  // corrected payload look like a same-key conflict to the backend instead
  // of a new attempt.
  let idempotencyKey = $state(crypto.randomUUID());

  // Set only on a submit that the backend rejected with `code:
  // "idempotency_conflict"` — same idempotency_key, different payload (see
  // registrations/views.py::_idempotency_replay_or_conflict_response).
  // Added 2026-09-24 (P1, gate review): the realistic way a guardian hits
  // this is the "lost response" case — an earlier submit actually
  // succeeded server-side, but the guardian never saw the confirmation
  // screen (closed the tab, a flaky connection dropped the response after
  // the request landed), so nothing here ever reset idempotencyKey via
  // handleEditEmail. They then change a field (or just retype the form)
  // and submit again under the SAME stale key — which now looks, to the
  // backend, exactly like a genuinely different payload reusing an old
  // key. A plain "something went wrong, try again" would be actively
  // misleading here (retrying blind risks a real second registration —
  // see handleResubmitAfterConflict's own comment), so this drives a
  // dedicated guidance banner instead of the generic `error` string.
  //
  // Deliberately NOT `lastSubmitPayload` (only ever written on a
  // confirmed 201, see its own comment above) — this is the opposite
  // case, a payload that was just REJECTED, captured fresh from the
  // submit attempt that hit the conflict.
  let idempotencyConflictPayload = $state<RegistrationSubmitPayload | null>(null);
  let idempotencyConflictBannerEl = $state<HTMLElement | null>(null);

  // Set only when handleSubmit's own missing-Relation check (below) blocks
  // the submit — a client-side guard that needs to flag each affected
  // control, not just the top-of-form banner (see submitProblems for the
  // banner's own, named version of the same check).
  // Cleared at the top of every submit attempt alongside `error`. See
  // relationshipMissing, which reads this together with each row's own
  // state so the caption disappears the moment a row is fixed, without any
  // explicit per-row reset.
  let relationshipMissingAttempted = $state(false);

  // Scroll/focus the failure banner into view on every new error — on this
  // 2000+px page a failed submit otherwise looks like nothing happened from
  // the submit button at the bottom (see build's blocker #2). Gated on
  // submitProblems too, not just `error`, since a purely client-side block
  // (e.g. only a missing Boende choice) can populate the itemized list
  // without ever setting a server-derived `error` string.
  $effect(() => {
    if ((error || submitProblems.length > 0) && errorBannerEl) {
      errorBannerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      errorBannerEl.focus();
    }
  });

  // Same reasoning as the effect above, for the idempotency-conflict
  // guidance banner — it replaces the plain `error` banner for this
  // specific outcome (see idempotencyConflictPayload's comment), so it
  // needs the same "make sure it's actually seen" treatment.
  $effect(() => {
    if (idempotencyConflictPayload && idempotencyConflictBannerEl) {
      idempotencyConflictBannerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      idempotencyConflictBannerEl.focus();
    }
  });

  function childAgeError(index: number): string | null {
    return extractFieldError(errorDetails, 'children', index);
  }

  // Attendee labels for the error summary (increment 5, 2026-09-28) — the
  // name as typed, falling back to the same ordinal labels already used
  // elsewhere on this page (register.parentLabel / checkin.childNumber, see
  // e.g. handleRemovePromoCode's own attendee list) once a first name is
  // empty, so a problem raised against a not-yet-named row still reads as
  // "who" rather than a bare index.
  function parentAttendeeLabel(parent: ParentRow, index: number): string {
    return parent.first_name.trim() || $t('register.parentLabel', { values: { number: index + 1 } });
  }

  function childAttendeeLabel(child: ChildRow, index: number): string {
    return child.first_name.trim() || $t('checkin.childNumber', { values: { number: index + 1 } });
  }

  // Scrolls/focuses the control a summary-banner line is about — the same
  // "make sure it's actually seen" treatment the banner itself gets (see
  // the $effect above), just aimed at one field instead of the banner.
  // Resolved by selector rather than a held element ref: these targets live
  // inside #each blocks keyed by array index, and a selector lookup avoids
  // keeping a parallel ref array in sync with parents/children.
  function focusOnProblem(problem: SubmitProblem) {
    if (!problem.focusSelector) return;
    const el = document.querySelector<HTMLElement>(problem.focusSelector);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.focus();
  }

  // R3 (registration dev-cycle round 4, increment 5 revision): generic
  // per-field invalid check for controls whose only "is this wrong" signal
  // lives in submitProblems, with no dedicated boolean of their own (unlike
  // e.g. relationshipMissing or the ticket-composition/sold-out warnings
  // above, which are already reactive against live field state). Matches
  // by SubmitProblem.id — the same id the banner line for this field uses.
  function hasProblem(id: string): boolean {
    return submitProblems.some((p) => p.id === id);
  }

  // Removes a submitProblems entry the instant the field it's about
  // changes, so the banner line and the field's own aria-invalid/danger
  // border disappear together rather than waiting for the next submit
  // attempt to re-validate. Fires on any edit, not just once the new value
  // is actually valid — a half-typed correction is still "the guardian is
  // looking at this now," and the real check runs again on the next submit
  // regardless. Once the last entry is gone, `error` (the banner's heading
  // line) is cleared too — handleSubmit and submitPayload's catch block
  // both only ever set `error` to the generic errorBannerHeading text
  // alongside a non-empty submitProblems, or (server path) to a specific
  // whole-form message with no matching field to clear it from — so
  // dropping `error` here only happens when it was that generic heading
  // with nothing left under it, never a real standalone message.
  function clearSubmitProblem(id: string) {
    if (submitProblems.length === 0) return;
    const next = submitProblems.filter((p) => p.id !== id);
    if (next.length === submitProblems.length) return;
    submitProblems = next;
    if (next.length === 0) error = '';
  }

  // Server-side counterpart to EMAIL_FORMAT_RE above (R2) — a 400 on
  // contact_email (e.g. the backend's own EmailField validation catches
  // something the client regex missed) must land in the exact same banner
  // item as the client-side checks, not the generic top-line message
  // extractErrorMessage would otherwise produce (see submitPayload's catch
  // block).
  function contactEmailServerError(details: unknown): boolean {
    if (!details || typeof details !== 'object') return false;
    const entry = (details as Record<string, unknown>).contact_email;
    return Array.isArray(entry) && entry.length > 0;
  }

  onMount(async () => {
    try {
      eventInfo = await registrationApi.getEvent(eventId);
    } catch (err) {
      console.error('Failed to load event info:', err);
      eventNotFound = true;
    } finally {
      loadingEvent = false;
    }
  });

  function applicableTicketTypes(isChild: boolean) {
    if (!eventInfo) return [];
    const kind = isChild ? 'child' : 'parent';
    return eventInfo.ticket_types.filter((tt) => tt.applies_to === kind || tt.applies_to === 'either');
  }

  function applicablePersonExtras(isChild: boolean): RegistrationExtraInfo[] {
    if (!eventInfo) return [];
    const kind = isChild ? 'child' : 'parent';
    return eventInfo.extras.filter(
      (extra) => extra.per_attendee && (extra.applies_to === kind || extra.applies_to === 'either')
    );
  }

  function registrationExtras(): RegistrationExtraInfo[] {
    return eventInfo ? eventInfo.extras.filter((extra) => !extra.per_attendee) : [];
  }

  function extraState(
    selections: Record<string, ExtraSelectionState>,
    extra: RegistrationExtraInfo
  ): ExtraSelectionState {
    // A required extra (case 3.2's must-choose-one, e.g. accommodation)
    // has no checkbox to toggle — it's mandatory, so it defaults selected
    // regardless of default_selected. What still needs an explicit answer
    // is the choice itself (see requiredChoiceMissing below).
    //
    // Non-required extras never start selected on this public guest form,
    // even when the event marks them default_selected — 2026-09-24 owner
    // decision (kitchen counts / data quality): an opt-out extra (e.g.
    // "Måltider hela helgen") was arriving pre-ticked for every attendee,
    // and two gate personas this round flagged it as "easy to overpay
    // without noticing." Staff/admin flows, event cloning, and demo seeding
    // still read default_selected as written (see events/services.py::clone,
    // seed_demo_data.py, registrations/views.py's event-info serialization)
    // — this function is the only place default_selected was ever turned
    // into a pre-checked box, so it's the one spot that changes.
    return (
      selections[extra.id] ?? {
        selected: extra.required,
        choiceId: '',
        quantity: 1
      }
    );
  }

  function setExtraSelected(
    selections: Record<string, ExtraSelectionState>,
    extra: RegistrationExtraInfo,
    selected: boolean
  ) {
    selections[extra.id] = { ...extraState(selections, extra), selected };
  }

  function setExtraChoice(
    selections: Record<string, ExtraSelectionState>,
    extra: RegistrationExtraInfo,
    choiceId: string
  ) {
    // Required extras have no checkbox — picking a choice is itself what
    // marks the extra as selected.
    selections[extra.id] = { ...extraState(selections, extra), choiceId, selected: true };
  }

  // A parent row only needs its Relation flagged once it would actually be
  // submitted — mirrors validParents' own first_name filter in handleSubmit,
  // so an empty, never-touched extra row doesn't light up red purely
  // because Relation renders before first_name is typed. Gated on
  // relationshipMissingAttempted so nothing is flagged before a submit is
  // ever tried; live-reactive after that, so picking a relationship clears
  // the row's own flag immediately with no explicit reset needed.
  function relationshipMissing(parent: ParentRow): boolean {
    return (
      relationshipMissingAttempted &&
      parent.first_name.trim().length > 0 &&
      !parent.relationship_type
    );
  }

  function requiredChoiceMissing(
    selections: Record<string, ExtraSelectionState>,
    extras: RegistrationExtraInfo[]
  ): boolean {
    return extras.some(
      (extra) => extra.required && extra.requires_choice && extraState(selections, extra).choiceId === ''
    );
  }

  function setExtraQuantity(
    selections: Record<string, ExtraSelectionState>,
    extra: RegistrationExtraInfo,
    quantity: number
  ) {
    selections[extra.id] = { ...extraState(selections, extra), quantity: Math.max(1, quantity) };
  }

  // Reads the browser's own computed validity straight off the date input
  // rather than re-parsing the string — the input already carries min/max
  // (see minBirthdateIso/todayIso above), so rangeUnderflow/rangeOverflow
  // is exactly "digit-by-digit typo" / "future date" with no extra logic
  // needed. Deliberately not `.valid` as a whole: an empty, merely
  // not-yet-filled field is also invalid (valueMissing) but must not be
  // treated as a bad date — there's no date to be wrong yet.
  function handleChildBirthdateChange(child: ChildRow, event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    child.birthdateRangeInvalid = input.validity.rangeUnderflow || input.validity.rangeOverflow;
    if (!child.birthdateRangeInvalid) {
      suggestChildTicketType(child);
    }
  }

  function suggestChildTicketType(child: ChildRow) {
    if (!eventInfo || child.ticketTypeId || !child.birthdate) return;
    const candidates = applicableTicketTypes(true).filter(
      (tt) =>
        (!tt.min_birthdate || child.birthdate >= tt.min_birthdate) &&
        (!tt.max_birthdate || child.birthdate <= tt.max_birthdate) &&
        // Capacity enforcement, 2026-09-24: never auto-suggest a sold-out
        // ticket — this only fires for a not-yet-selected field (see the
        // guard above), so ticketAvailable's isSelected=false is always
        // right here.
        tt.available
    );
    // Prefer a type with an actual age window over one with none — an
    // unbounded "either" type (e.g. "All inclusive", no age limit) always
    // matches and must not shadow a more specific age-tiered type (e.g.
    // "0-6 år") just because it happens to sort first. Only fall back to
    // an unbounded type when nothing more specific matches.
    const bounded = candidates.find((tt) => tt.min_birthdate || tt.max_birthdate);
    const match = bounded ?? candidates[0];
    if (match) {
      child.ticketTypeId = match.id;
      child.promoReset = false;
      settlePromoRemovalMessageIfDone();
    }
  }

  // Follow-up (confirmation-persona gate, same revision as R1/R2 above): the
  // aria-live removal line under the promo field ("Koden togs bort. VIP-helg
  // ... välj ny biljettyp för Förälder 1.") was announcing a problem that
  // could already be fixed — it stayed up even once every named attendee
  // had repicked a ticket, while the per-row caption correctly disappeared.
  // Dropped entirely (not downgraded to a bare "code removed") once no row
  // is still in the reset state: at that point every row the message named
  // has its own resolved selection right there in the form, so the
  // page-level line has nothing left to add — repeating "code removed"
  // would be a stale echo, not new information.
  function settlePromoRemovalMessageIfDone() {
    if (!promoRemovalMessage) return;
    const stillReset = parents.some((p) => p.promoReset) || children.some((c) => c.promoReset);
    if (!stillReset) promoRemovalMessage = '';
  }

  // Write-back handlers for the parent/child ticket-type <select>s below —
  // added for R1 (registration dev-cycle round 4, increment 3 revision).
  // These selects used to be bind:value, which desyncs from state when the
  // option list changes (a promo code unlocking/retracting a hidden ticket
  // type, via checkPromoCode/retractPromoUnlockedTicketTypes reassigning
  // eventInfo.ticket_types) while the select is focused: svelte 5.43.14's
  // bind_select_value only writes select.__value from its own state→DOM
  // effect, which early-returns when the change came from the select's own
  // focused batch, so __value sticks at the value the select had at mount
  // ("") — and init_select's MutationObserver on the changed <option>
  // childList then reasserts that stale __value onto the DOM, silently
  // reverting the guardian's own pick to the placeholder while the
  // underlying state (parent.ticketTypeId) is still correct. One-way
  // value={…} + an explicit onchange write-back sidesteps that internal
  // effect entirely — the DOM is only ever driven by fresh renders and this
  // handler, never by bind:value's own desyncing effect. See page.test.ts's
  // "R1 select desync" tests, which reproduce the stale-DOM symptom against
  // the old bind:value markup (confirmed failing pre-fix) and pass against
  // this.
  function handleParentTicketTypeChange(index: number, value: string) {
    parents[index].ticketTypeId = value;
    if (value) {
      parents[index].promoReset = false;
      settlePromoRemovalMessageIfDone();
      clearSubmitProblem(`parent-ticket-type-${index}`);
    }
  }

  function handleChildTicketTypeChange(index: number, value: string) {
    children[index].ticketTypeId = value;
    if (value) {
      children[index].promoReset = false;
      settlePromoRemovalMessageIfDone();
      clearSubmitProblem(`child-ticket-type-${index}`);
    }
  }

  // Whether a child's entered birthdate falls inside a ticket type's
  // min/max birthdate window. No birthdate yet => everything is eligible
  // (constraint: nothing is disabled until we actually know the birthdate).
  function childTicketEligible(ticketType: RegistrationTicketType, birthdate: string): boolean {
    if (!birthdate) return true;
    const minOk = !ticketType.min_birthdate || birthdate >= ticketType.min_birthdate;
    const maxOk = !ticketType.max_birthdate || birthdate <= ticketType.max_birthdate;
    return minOk && maxOk;
  }

  // Renders a ticket type's age window as prose, e.g. "0–12 yrs". Mirrors
  // birthdateProse's age-at-event-start-date convention. min_birthdate is
  // the *oldest* allowed birthdate (bounds the type's max age) and
  // max_birthdate is the *youngest* allowed birthdate (bounds the type's
  // min age) — the naming is about the birthdate value, not the age.
  function ticketAgeRangeLabel(ticketType: RegistrationTicketType, asOfIso: string): string {
    const maxAge = ticketType.min_birthdate ? ageAt(ticketType.min_birthdate, asOfIso) : null;
    const minAge = ticketType.max_birthdate ? ageAt(ticketType.max_birthdate, asOfIso) : null;
    if (minAge != null && maxAge != null) {
      return $t('register.ticketAgeRangeBoth', { values: { min: minAge, max: maxAge } });
    }
    if (minAge != null) return $t('register.ticketAgeRangeMin', { values: { min: minAge } });
    if (maxAge != null) return $t('register.ticketAgeRangeMax', { values: { max: maxAge } });
    return '';
  }

  // A staff-authored ticket name that already states its own age window
  // (e.g. "Barn (0-12 år)") makes a second, independently-formatted range
  // repeated in the warning below pure noise — and on a narrow screen it's
  // the nested-parens part that gets clipped. Two numbers joined by a
  // hyphen/en dash is a good-enough proxy for "the name already says this".
  function nameStatesAgeRange(name: string): boolean {
    return /\d+\s*[-–]\s*\d+/.test(name);
  }

  // If a birthdate edit makes an *already-selected* ticket ineligible, we
  // deliberately keep the selection rather than silently clearing it — the
  // guardian picked it for a reason (maybe the birthdate typo is what's
  // wrong, not the ticket), and clearing it would erase that signal and
  // could even let a required-extra/composition state quietly go stale.
  // Instead we surface a clear, visible warning next to the field so they
  // can decide whether to fix the birthdate or the ticket. The server is
  // still the real gate at submission either way.
  function childSelectedTicketWarning(child: ChildRow): string | null {
    // An invalid birthdate (see birthdateRangeInvalid) was never a real
    // date to check tickets against — don't let it masquerade as a ticket
    // problem.
    if (!child.ticketTypeId || !child.birthdate || !eventInfo || child.birthdateRangeInvalid) {
      return null;
    }
    const ticketType = eventInfo.ticket_types.find((tt) => tt.id === child.ticketTypeId);
    if (!ticketType || childTicketEligible(ticketType, child.birthdate)) return null;
    if (nameStatesAgeRange(ticketType.name)) {
      return $t('register.ticketTypeIneligibleWarningNoRange', { values: { name: ticketType.name } });
    }
    const asOfIso = eventInfo.start_date ?? todayIso;
    const range = ticketAgeRangeLabel(ticketType, asOfIso);
    return $t('register.ticketTypeIneligibleWarning', { values: { name: ticketType.name, range } });
  }

  // A child's ticket select can be flagged for three independent reasons —
  // age-window (childSelectedTicketWarning), composition
  // (ticketCompositionWarning), and now sold-out (ticketSoldOutWarning) —
  // each with its own paragraph/id below the field. This combines them for
  // the select's own aria-invalid/aria-describedby so the control itself is
  // marked whichever reason (or several) applies, matching the parent
  // select's version.
  function childTicketDescribedBy(index: number, child: ChildRow): string | undefined {
    const ids: string[] = [];
    if (childSelectedTicketWarning(child)) ids.push(`child-ticket-ineligible-${index}`);
    if (ticketCompositionWarning(child.ticketTypeId)) ids.push(`child-ticket-composition-${index}`);
    if (ticketSoldOutWarning(child.ticketTypeId)) ids.push(`child-ticket-sold-out-${index}`);
    if (child.promoReset) ids.push(`child-ticket-promo-reset-${index}`);
    return ids.length > 0 ? ids.join(' ') : undefined;
  }

  function buildExtraSelections(
    selections: Record<string, ExtraSelectionState>,
    extras: RegistrationExtraInfo[]
  ): RegistrationExtraSelectionPayload[] {
    const result: RegistrationExtraSelectionPayload[] = [];
    for (const extra of extras) {
      // Use extraState's fallback, not a raw lookup — a required extra
      // (no checkbox; see extraState) the guardian never explicitly
      // toggled must still submit as selected, matching what the UI shows.
      // Reading selections[extra.id] directly here would drop it from the
      // payload while the UI still showed it checked. Non-required extras
      // default to NOT selected (see extraState), so this fallback is a
      // no-op for those unless the guardian actually ticked the box.
      const state = extraState(selections, extra);
      if (!state.selected) continue;
      result.push({
        extra: extra.id,
        choice: state.choiceId || null,
        quantity: state.quantity || 1
      });
    }
    return result;
  }

  function priceOf(extra: RegistrationExtraInfo, state: ExtraSelectionState): number {
    if (!state.selected) return 0;
    const choice = extra.choices.find((c) => c.id === state.choiceId);
    const unit = parseFloat(extra.price) + (choice ? parseFloat(choice.price_delta) : 0);
    return unit * (state.quantity || 1);
  }

  // Distinct-attendee counts per selected ticket type — mirrors the
  // server-side grouping in registrations/ticket_rules.py::
  // validate_ticket_composition so the UX hint below never contradicts
  // what the server will actually enforce. UX hint only; the server call
  // is the real enforcement (see registrationWindowStatus's precedent).
  let ticketTypeCounts = $derived.by(() => {
    const counts: Record<string, number> = {};
    for (const person of [...parents, ...children]) {
      if (person.ticketTypeId) {
        counts[person.ticketTypeId] = (counts[person.ticketTypeId] ?? 0) + 1;
      }
    }
    return counts;
  });

  function ticketCompositionWarning(ticketTypeId: string): string | null {
    if (!eventInfo || !ticketTypeId) return null;
    const ticketType = eventInfo.ticket_types.find((tt) => tt.id === ticketTypeId);
    if (!ticketType?.requires_ticket_type_id) return null;
    const requiredType = eventInfo.ticket_types.find(
      (tt) => tt.id === ticketType.requires_ticket_type_id
    );
    const requiredName = requiredType?.name ?? '';
    const requiredCount = ticketTypeCounts[ticketType.requires_ticket_type_id] ?? 0;
    if (requiredCount === 0) {
      return $t('register.ticketRequiresOther', {
        values: { name: ticketType.name, required: requiredName }
      });
    }
    if (ticketType.max_per_required != null) {
      const count = ticketTypeCounts[ticketTypeId] ?? 0;
      if (count > requiredCount * ticketType.max_per_required) {
        return $t('register.ticketCapExceeded', {
          values: { name: ticketType.name, max: ticketType.max_per_required, required: requiredName }
        });
      }
    }
    return null;
  }

  // Whether *picking* this ticket type is currently allowed — mirrors
  // registrations/ticket_rules.py::validate_ticket_composition so the
  // option list never offers a combination the server will reject.
  // isSelected is whether this option is the row's *own current* pick:
  // same convention as childTicketEligible/disabled above — a selection
  // that was valid when made and has since gone bad (the required ticket
  // was changed away, or someone else's pick pushed the count over cap)
  // is NOT specially exempted here (still comes back disabled, same as
  // the age-window case), it's ticketCompositionWarning below that keeps
  // it selected and flags it rather than this function silently un-
  // selecting it. isSelected only matters for the cap arithmetic: this
  // row's own pick is already inside `count`, so the boundary (exactly at
  // cap) reads as fine for the row that's already there, but as "full,
  // don't add another" for everyone else.
  function ticketCompositionEligible(ticketType: RegistrationTicketType, isSelected: boolean): boolean {
    if (!ticketType.requires_ticket_type_id) return true;
    const requiredCount = ticketTypeCounts[ticketType.requires_ticket_type_id] ?? 0;
    if (requiredCount === 0) return false;
    if (ticketType.max_per_required == null) return true;
    const count = ticketTypeCounts[ticketType.id] ?? 0;
    const cap = requiredCount * ticketType.max_per_required;
    return isSelected ? count <= cap : count < cap;
  }

  // Capacity enforcement, 2026-09-24 (registration dev-cycle round 4,
  // increment 2). Mirrors ticketCompositionEligible's isSelected
  // allowance: a ticket that was available when picked and has since sold
  // out (someone else took the last seat while this guardian was still
  // filling in the form) stays selected rather than being silently
  // cleared — same "don't erase the signal" stance as
  // childSelectedTicketWarning above — but is never offered fresh to
  // anyone else.
  function ticketAvailable(ticketType: RegistrationTicketType, isSelected: boolean): boolean {
    return ticketType.available || isSelected;
  }

  // Field-level warning for an already-selected ticket that has since sold
  // out. Shares ticketCompositionWarning's shape (keyed by ticketTypeId, so
  // one function serves both the parent and child selects) rather than
  // childSelectedTicketWarning's — this has no birthdate/eligibility
  // precondition to check first.
  function ticketSoldOutWarning(ticketTypeId: string): string | null {
    if (!eventInfo || !ticketTypeId) return null;
    const ticketType = eventInfo.ticket_types.find((tt) => tt.id === ticketTypeId);
    if (!ticketType || ticketType.available) return null;
    return $t('register.ticketSoldOutWarning', { values: { name: ticketType.name } });
  }

  // Short "(requires X)" / "(max N per X)" marker for an ineligible option
  // in the open list — mirrors ticketAgeRangeLabel's role for the age
  // case: the full sentence lives in ticketCompositionWarning below the
  // select, this stays short so the option row doesn't wrap.
  function ticketCompositionOptionMarker(ticketType: RegistrationTicketType): string {
    if (!eventInfo || !ticketType.requires_ticket_type_id) return '';
    const requiredType = eventInfo.ticket_types.find(
      (tt) => tt.id === ticketType.requires_ticket_type_id
    );
    const requiredName = requiredType?.name ?? '';
    const requiredCount = ticketTypeCounts[ticketType.requires_ticket_type_id] ?? 0;
    if (requiredCount === 0) {
      return $t('register.ticketCompositionOptionRequires', { values: { required: requiredName } });
    }
    if (ticketType.max_per_required != null) {
      return $t('register.ticketCompositionOptionCapReached', {
        values: { max: ticketType.max_per_required, required: requiredName }
      });
    }
    return '';
  }

  // Full <option> label shared by both the parent and child selects.
  // birthdate is '' for a parent row, and childTicketEligible treats an
  // empty birthdate as always-eligible, so the age check is a no-op there
  // — this stays one function rather than forking parent/child copies.
  // isSelected drops both markers (same reasoning as childTicketOptionLabel
  // before this increment): the reason is already shown as the field-level
  // warning right below the select.
  function ticketOptionLabel(
    ticketType: RegistrationTicketType,
    birthdate: string,
    isSelected: boolean
  ): string {
    const base = `${ticketType.name} — ${formatCurrency(ticketType.price)} kr`;
    if (isSelected) return base;
    if (!ticketAvailable(ticketType, isSelected)) {
      return `${base} (${$t('register.ticketSoldOutMarker')})`;
    }
    if (!childTicketEligible(ticketType, birthdate)) {
      const asOfIso = eventInfo?.start_date ?? todayIso;
      const range = ticketAgeRangeLabel(ticketType, asOfIso);
      return range ? `${base} (${range})` : base;
    }
    if (!ticketCompositionEligible(ticketType, isSelected)) {
      const marker = ticketCompositionOptionMarker(ticketType);
      return marker ? `${base} (${marker})` : base;
    }
    return base;
  }

  let runningTotal = $derived.by(() => {
    if (!eventInfo) return 0;
    let total = 0;
    for (const parent of parents) {
      const ticketType = eventInfo.ticket_types.find((tt) => tt.id === parent.ticketTypeId);
      if (ticketType) total += parseFloat(ticketType.price);
      for (const extra of applicablePersonExtras(false)) {
        total += priceOf(extra, extraState(parent.extraSelections, extra));
      }
    }
    for (const child of children) {
      const ticketType = eventInfo.ticket_types.find((tt) => tt.id === child.ticketTypeId);
      if (ticketType) total += parseFloat(ticketType.price);
      for (const extra of applicablePersonExtras(true)) {
        total += priceOf(extra, extraState(child.extraSelections, extra));
      }
    }
    for (const extra of registrationExtras()) {
      total += priceOf(extra, extraState(registrationExtraSelections, extra));
    }
    return total;
  });

  // The running total's arithmetic already prices whatever is currently
  // selected, including a ticket a birthdate edit just flagged as
  // ineligible (see childSelectedTicketWarning's keep-the-selection
  // decision) — the total must not silently exclude it, but it also must
  // not present that figure as settled. This only flags it; the price
  // itself is untouched. Also covers a composition violation (missing/
  // removed required ticket, or over cap) on either a parent or a child —
  // e.g. removing the person holding the only Familjebiljett leaves the
  // dependent "familjemedlem" selections in place but no longer valid, and
  // that must show here too, not just as a per-row caption.
  let hasIneligibleTicketSelection = $derived(
    children.some(
      (child) =>
        childSelectedTicketWarning(child) !== null ||
        ticketCompositionWarning(child.ticketTypeId) !== null
    ) || parents.some((parent) => ticketCompositionWarning(parent.ticketTypeId) !== null)
  );

  // Undoes checkPromoCode's is_hidden merge (see its own comment) once the
  // code that earned it is no longer in effect — called both when a fresh
  // checkPromoCode run is about to replace it and, from the promo input's
  // on:input handler, the moment the guardian edits the code away without
  // re-validating. Without this, a hidden VIP type a code unlocked stays a
  // pickable option (and, worse, stays *selected* on whichever attendee row
  // already picked it) after the code that unlocked it is gone — the
  // server then rejects that selection at submit with the same generic
  // "Invalid ticket type for this event." a nonexistent type gets (see
  // _validate_ticket_type_for_attendee's is_hidden gate), which is a
  // confusing dead end rather than a clear "your code was removed" signal.
  // Clearing the selection here, rather than merely warning like
  // childSelectedTicketWarning does for an age/composition change, is the
  // deliberate difference: those tickets are still real, visible options
  // the guardian can knowingly keep; a retracted hidden type is not an
  // option at all anymore, so nothing legitimate is being erased.
  function retractPromoUnlockedTicketTypes() {
    if (promoCodeUnlockedIds.length === 0 || !eventInfo) return;
    const removed = new Set(promoCodeUnlockedIds);
    eventInfo = {
      ...eventInfo,
      ticket_types: eventInfo.ticket_types.filter((tt) => !removed.has(tt.id))
    };
    for (const parent of parents) {
      if (removed.has(parent.ticketTypeId)) parent.ticketTypeId = '';
    }
    for (const child of children) {
      if (removed.has(child.ticketTypeId)) child.ticketTypeId = '';
    }
    promoCodeUnlockedIds = [];
  }

  async function checkPromoCode() {
    const code = promoCode.trim();
    promoCodeError = '';
    promoCodeValidation = null;
    promoCodeAppliedValue = '';
    promoRemovalMessage = '';
    retractPromoUnlockedTicketTypes();
    if (!code || !eventInfo) return;

    promoCodeChecking = true;
    try {
      const result = await registrationApi.validatePromoCode(eventId, code);
      if (!result.valid) {
        promoCodeError = $t('register.promoCodeInvalid');
        return;
      }
      promoCodeValidation = result;
      promoCodeAppliedValue = code;
      // Reveal any is_hidden ticket types this code unlocks (e.g. VIP) by
      // merging them into the local list — applicableTicketTypes/
      // suggestChildTicketType then pick them up with no further changes.
      const unlocked = result.unlocks_ticket_types ?? [];
      const existingIds = new Set(eventInfo.ticket_types.map((tt) => tt.id));
      const newlyUnlocked = unlocked.filter((tt) => !existingIds.has(tt.id));
      if (newlyUnlocked.length > 0) {
        eventInfo = { ...eventInfo, ticket_types: [...eventInfo.ticket_types, ...newlyUnlocked] };
        promoCodeUnlockedIds = newlyUnlocked.map((tt) => tt.id);
      }
    } catch (err) {
      console.error('Promo code validation failed:', err);
      promoCodeError = $t('register.promoCodeInvalid');
    } finally {
      promoCodeChecking = false;
    }
  }

  // R3 (registration dev-cycle round 4, increment 3 revision): the applied
  // confirmation states the concrete effect rather than a bare "Code
  // applied." — built from the exact same validation result the discount
  // preview (discountAmount below) and the running total already use, so
  // this line can never say something the total contradicts. Returns ''
  // when there's nothing applied (guarded at the call site, not here, since
  // the empty case never renders).
  function promoAppliedMessage(): string {
    if (!promoCodeValidation?.valid) return '';
    const parts: string[] = [];
    const value = parseFloat(promoCodeValidation.discount_value ?? '0');
    if (value > 0) {
      parts.push(
        promoCodeValidation.discount_type === 'percent'
          ? $t('register.promoEffectPercent', { values: { percent: value } })
          : $t('register.promoEffectFixed', { values: { amount: formatCurrency(value) } })
      );
    }
    const unlocked = promoCodeValidation.unlocks_ticket_types ?? [];
    if (unlocked.length > 0) {
      parts.push(
        $t('register.promoEffectUnlocks', {
          values: { names: unlocked.map((tt) => tt.name).join(', ') }
        })
      );
    }
    const prefix = $t('register.promoCodeAppliedPrefix');
    return parts.length > 0 ? `${prefix} – ${parts.join(' ')}` : `${prefix}.`;
  }

  // R2 (registration dev-cycle round 4, increment 3 revision): "Ta bort" on
  // the applied-code chip — an explicit un-apply, replacing the old silent
  // one where editing the text past a validated code quietly dropped it.
  // Because it's explicit, it earns an explicit confirmation: which ticket
  // type just disappeared and from which attendee(s), captured BEFORE
  // retractPromoUnlockedTicketTypes clears those selections (afterwards
  // there's nothing left to point at). See promoRemovalMessage and
  // ParentRow/ChildRow.promoReset for where this lands in the UI.
  function handleRemovePromoCode() {
    const removedIds = new Set(promoCodeUnlockedIds);
    const removedNames = eventInfo
      ? eventInfo.ticket_types.filter((tt) => removedIds.has(tt.id)).map((tt) => tt.name)
      : [];
    const affectedParents = parents
      .map((p, i) => (removedIds.has(p.ticketTypeId) ? i : -1))
      .filter((i) => i >= 0);
    const affectedChildren = children
      .map((c, i) => (removedIds.has(c.ticketTypeId) ? i : -1))
      .filter((i) => i >= 0);

    retractPromoUnlockedTicketTypes();

    for (const i of affectedParents) parents[i].promoReset = true;
    for (const i of affectedChildren) children[i].promoReset = true;

    promoCode = '';
    promoCodeError = '';
    promoCodeValidation = null;
    promoCodeAppliedValue = '';

    if (removedNames.length > 0 && (affectedParents.length > 0 || affectedChildren.length > 0)) {
      const attendeeLabels = [
        ...affectedParents.map((i) => $t('register.parentLabel', { values: { number: i + 1 } })),
        ...affectedChildren.map((i) => $t('checkin.childNumber', { values: { number: i + 1 } }))
      ];
      promoRemovalMessage = $t('register.promoRemovedWithReset', {
        values: { ticket: removedNames.join(', '), attendees: attendeeLabels.join(', ') }
      });
    } else {
      promoRemovalMessage = $t('register.promoRemoved');
    }
  }

  // Cosmetic preview only, mirroring pricing.py::calculate_discount's
  // scoping rule — the server recomputes and snapshots the real discount
  // from scratch at submission, this never gets trusted for the charge.
  let discountAmount = $derived.by(() => {
    if (!promoCodeValidation?.valid || !eventInfo) return 0;
    const scopedIds = promoCodeValidation.applies_to_ticket_type_ids ?? [];

    let base = runningTotal;
    if (scopedIds.length > 0) {
      const scopedSet = new Set(scopedIds);
      base = 0;
      for (const row of [...parents, ...children]) {
        if (!scopedSet.has(row.ticketTypeId)) continue;
        const ticketType = eventInfo.ticket_types.find((tt) => tt.id === row.ticketTypeId);
        if (ticketType) base += parseFloat(ticketType.price);
      }
    }

    const value = parseFloat(promoCodeValidation.discount_value ?? '0');
    const raw = promoCodeValidation.discount_type === 'percent' ? (base * value) / 100 : value;
    return Math.min(raw, base);
  });

  let discountedTotal = $derived(Math.max(runningTotal - discountAmount, 0));

  function handleAddParent() {
    parents = [...parents, emptyParent()];
  }

  function handleRemoveParent(index: number) {
    parents = parents.filter((_, i) => i !== index);
  }

  function handleAddChild() {
    children = [...children, emptyChild()];
  }

  function handleRemoveChild(index: number) {
    children = children.filter((_, i) => i !== index);
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();

    // `disabled` on the submit button is flushed a microtask after
    // `submitting` is set (see finally block below), so a fast second tap
    // can still land here before the DOM catches up — guard the handler
    // itself rather than relying on the disabled attribute alone.
    if (submitting) return;

    error = '';
    errorDetails = null;
    submitProblems = [];
    // A fresh manual submit from the form itself is never the "lost
    // response, resubmit under a fresh key" recovery flow — clear any
    // stale guidance banner from an earlier attempt so it doesn't linger
    // next to an unrelated new error (or nothing at all, on success).
    idempotencyConflictPayload = null;
    relationshipMissingAttempted = false;

    if (isPreview) return;

    // Increment 5 (2026-09-28), driven by a gate finding: a parent who
    // submitted without picking Boende (a required per-attendee choice)
    // got a generic "a required choice is missing for everyone"-style
    // message with no hint of which field or which person, and had to
    // hunt through the whole form. Every check below now pushes onto
    // `problems` instead of returning on the first failure, so the banner
    // can name every missing/invalid thing at once — one line per problem,
    // each naming the attendee it's about where there is one (see
    // parentAttendeeLabel/childAttendeeLabel). Checks that also drive an
    // inline per-field caption (relationshipMissingAttempted, promoCodeError)
    // still set that side state here, unchanged — the banner line and the
    // inline caption are the same problem shown twice, not two problems.
    const problems: SubmitProblem[] = [];

    // A promo code that's typed but not currently validated must never
    // ride along silently in the submit payload — that's exactly the "a
    // rejected code still submits" gap this guard closes (registration
    // dev-cycle round 4, increment 3). "Not currently validated" covers
    // all three ways this happens: never clicked Apply, clicked Apply and
    // it came back invalid (promoCodeError is already showing), or applied
    // successfully and then edited the text afterwards — the promo
    // input's own on:input handler nulls promoCodeValidation on every
    // keystroke (see its comment), so by the time this runs
    // "promoCodeValidation is non-null" and "the box still holds the code
    // it was validated against" are the same fact. The backend would
    // reject an invalid code here too (see _resolve_promo_code), but
    // failing fast client-side, at the field, is both faster and puts the
    // message where the guardian is looking instead of in the generic
    // top-of-form banner.
    if (promoCode.trim() && !promoCodeValidation?.valid) {
      promoCodeError = $t('register.promoCodeNotApplied');
      problems.push({
        id: 'promo-code',
        message: $t('register.promoCodeNotApplied'),
        focusSelector: '#promo-code-input'
      });
    }

    // Empty and malformed both read the same message and land on the same
    // banner item (R2) — "a valid email address is required" is true
    // either way, and novalidate (see the form's own comment) means this
    // is now the only format check running before the round trip.
    if (!contactEmail.trim() || !EMAIL_FORMAT_RE.test(contactEmail.trim())) {
      problems.push({
        id: 'contact-email',
        message: $t('register.contactEmailRequired'),
        focusSelector: '#contact-email'
      });
    }

    children.forEach((child, index) => {
      if (!child.first_name.trim() || !child.last_name.trim() || !child.birthdate.trim()) {
        problems.push({
          id: `child-info-${index}`,
          message: $t('register.childInfoIncomplete', {
            values: { name: childAttendeeLabel(child, index) }
          }),
          focusSelector: `#child-first-name-${index}`
        });
      }
      if (child.healthInfoStatus === 'consented' && !child.consentNoticeShared) {
        problems.push({
          id: `child-consent-${index}`,
          message: $t('checkin.healthConsentRequired'),
          focusSelector: `[data-testid="child-consent-attest-${index}"]`
        });
      }
    });

    // A parent row with a blank first name is dropped here rather than
    // required — this form does NOT enforce "at least one named
    // parent/guardian per registration" (a children-only registration
    // passes both here and server-side). That's deliberate for now: the
    // owner deferred the actual guardian requirement to a separate design
    // session rather than have this increment invent one (knowitall task
    // c129cd8d). Until that lands, Förälder 1's first name has no required
    // star (see the label below) and this filter's behavior is unchanged —
    // don't add a guardian requirement here.
    const validParents = parents.filter((p) => p.first_name.trim().length > 0);
    const validParentEntries = parents
      .map((p, index) => ({ p, index }))
      .filter(({ p }) => p.first_name.trim().length > 0);

    if (children.length === 0 && validParents.length === 0) {
      problems.push({
        id: 'at-least-one-member',
        message: $t('checkin.atLeastOneMemberRequired'),
        focusSelector: null
      });
    }

    for (const { p, index } of validParentEntries) {
      if (p.phone && !isValidPhone(p.phone)) {
        problems.push({
          id: `parent-phone-${index}`,
          message: $t('checkin.invalidPhone'),
          focusSelector: `#parent-phone-${index}`
        });
      }
      if (p.healthInfoStatus === 'consented' && !p.consentNoticeShared) {
        problems.push({
          id: `parent-consent-${index}`,
          message: $t('register.adultHealthConsentRequired'),
          focusSelector: `[data-testid="parent-consent-attest-parent-${index}"]`
        });
      }
    }

    // 2026-09-24 owner decision: Relation has no default (see emptyParent
    // above) — the parent must actively choose it. relationshipMissingAttempted
    // still drives each affected row's own inline caption/aria-invalid via
    // relationshipMissing; the banner line below is the same problem, named.
    const parentsMissingRelationship = validParentEntries.filter(({ p }) => !p.relationship_type);
    if (parentsMissingRelationship.length > 0) {
      relationshipMissingAttempted = true;
      for (const { p, index } of parentsMissingRelationship) {
        problems.push({
          id: `parent-relationship-${index}`,
          message: $t('register.relationshipRequired', {
            values: { name: parentAttendeeLabel(p, index) }
          }),
          focusSelector: `[data-testid="parent-relationship-${index}"]`
        });
      }
    }

    const requiresTicketType = !!eventInfo && eventInfo.ticket_types.length > 0;
    if (requiresTicketType) {
      for (const { p, index } of validParentEntries) {
        if (!p.ticketTypeId) {
          problems.push({
            id: `parent-ticket-type-${index}`,
            message: $t('register.ticketTypeRequired', {
              values: { name: parentAttendeeLabel(p, index) }
            }),
            focusSelector: `[data-testid="parent-ticket-type-${index}"]`
          });
        }
      }
      children.forEach((child, index) => {
        if (!child.ticketTypeId) {
          problems.push({
            id: `child-ticket-type-${index}`,
            message: $t('register.ticketTypeRequired', {
              values: { name: childAttendeeLabel(child, index) }
            }),
            focusSelector: `[data-testid="child-ticket-type-${index}"]`
          });
        }
      });
    }

    for (const { p, index } of validParentEntries) {
      for (const extra of applicablePersonExtras(false)) {
        if (extra.required && extra.requires_choice && extraState(p.extraSelections, extra).choiceId === '') {
          problems.push({
            id: `parent-extra-${extra.id}-${index}`,
            message: $t('register.requiredExtraMissing', {
              values: { extra: extra.name, name: parentAttendeeLabel(p, index) }
            }),
            focusSelector: `[data-testid="parent-extra-required-${extra.id}-${index}"] input[type="radio"]`
          });
        }
      }
    }
    children.forEach((child, index) => {
      for (const extra of applicablePersonExtras(true)) {
        if (
          extra.required &&
          extra.requires_choice &&
          extraState(child.extraSelections, extra).choiceId === ''
        ) {
          problems.push({
            id: `child-extra-${extra.id}-${index}`,
            message: $t('register.requiredExtraMissing', {
              values: { extra: extra.name, name: childAttendeeLabel(child, index) }
            }),
            focusSelector: `[data-testid="child-extra-required-${extra.id}-${index}"] input[type="radio"]`
          });
        }
      }
    });
    for (const extra of registrationExtras()) {
      if (
        extra.required &&
        extra.requires_choice &&
        extraState(registrationExtraSelections, extra).choiceId === ''
      ) {
        problems.push({
          id: `registration-extra-${extra.id}`,
          message: $t('register.requiredExtraMissingRegistration', { values: { extra: extra.name } }),
          focusSelector: `[data-testid="registration-extra-required-${extra.id}"] input[type="radio"]`
        });
      }
    }

    if (problems.length > 0) {
      submitProblems = problems;
      error = $t('register.errorBannerHeading');
      return;
    }

    const statusMap: Record<HealthInfoStatus, HealthConsentStatus> = {
      none: 'not_applicable',
      consented: 'granted',
      declined: 'declined'
    };

    const payload: RegistrationSubmitPayload = {
      event: eventId,
      last_name: familyName.trim(),
      contact_email: contactEmail.trim(),
      parents: validParents.map((p) => ({
        first_name: p.first_name.trim(),
        last_name: p.last_name.trim(),
        phone: p.phone.trim(),
        email: p.email.trim(),
        relationship_type: p.relationship_type,
        allergies: p.healthInfoStatus === 'consented' ? p.allergies : '',
        notes: p.healthInfoStatus === 'consented' ? p.notes : '',
        health_consent_status: statusMap[p.healthInfoStatus],
        ticket_type: p.ticketTypeId || null,
        extras: buildExtraSelections(p.extraSelections, applicablePersonExtras(false))
      })),
      children: children.map((child) => ({
        first_name: child.first_name.trim(),
        last_name: child.last_name.trim(),
        birthdate: child.birthdate,
        allergies: child.healthInfoStatus === 'consented' ? child.allergies : '',
        notes: child.healthInfoStatus === 'consented' ? child.notes : '',
        health_consent_status: statusMap[child.healthInfoStatus],
        ticket_type: child.ticketTypeId || null,
        extras: buildExtraSelections(child.extraSelections, applicablePersonExtras(true))
      })),
      extras: buildExtraSelections(registrationExtraSelections, registrationExtras()),
      promo_code: promoCode.trim(),
      website,
      idempotency_key: idempotencyKey
    };

    await submitPayload(payload);
  }

  // Shared by handleSubmit above and handleResubmitAfterConflict below —
  // both end up POSTing a fully-built RegistrationSubmitPayload and need
  // identical success/failure handling. Split out 2026-09-24 (P1, gate
  // review) when the idempotency-conflict recovery button needed the exact
  // same submit-and-handle-response logic as the main form, just with a
  // different payload/key.
  async function submitPayload(payload: RegistrationSubmitPayload) {
    submitting = true;
    try {
      const response = await registrationApi.submit(payload);
      if (response.code === 'registration_already_pending') {
        // The backend's dedup path was hit — this payload's data (including
        // anything just edited/added) was NOT saved. Route to the dedicated
        // "already pending" screen instead of the normal success screen; see
        // pendingDuplicate's own comment for the incident this fixes.
        pendingDuplicate = {
          referenceCode: response.reference_code,
          emailResent: response.email_sent === true
        };
        idempotencyConflictPayload = null;
        submitProblems = [];
        error = '';
        submitted = false;
        return;
      }
      referenceCode = response.reference_code;
      // Kept so the confirmation screen's "resend" action can replay the
      // exact same submission — the backend's own dedup logic (same event +
      // contact_email while still pending_verification) treats a repeat as
      // a resend rather than a duplicate, cooldown and all, so there's no
      // separate resend endpoint to build or throttle here. handleResend
      // below deliberately strips idempotency_key before replaying this —
      // that field means "retry, don't redo the work" and a resend is the
      // opposite: the guardian is explicitly asking for a new email.
      // Replaying it under the same key would just hand back this same
      // cached response and never touch send_verification_email at all.
      lastSubmitPayload = payload;
      resendStatus = null;
      // The registration is saved either way; this only says whether the
      // email actually left. Only an explicit false counts as a failure —
      // the backend omits the field on its "already sent recently" path.
      emailSent = response.email_sent !== false;
      idempotencyConflictPayload = null;
      submitProblems = [];
      submitted = true;
    } catch (err) {
      console.error('Registration submission failed:', err);
      const apiError = err as ApiError;
      errorDetails = apiError.details ?? null;
      // Check the idempotency-conflict `code` BEFORE calling
      // extractErrorMessage below. That helper's fallback walks
      // Object.values(details) looking for the first string it finds —
      // with no code check first, it would happily surface the bare
      // `"idempotency_conflict"` string itself (just another value in the
      // body) as if it were a human-readable message, instead of routing
      // to the dedicated guidance banner this state actually needs. See
      // registrations/views.py::_idempotency_replay_or_conflict_response
      // for where the backend sets this.
      const code = (apiError.details as { code?: string } | null)?.code;
      if (code === 'idempotency_conflict') {
        idempotencyConflictPayload = payload;
        return;
      }
      // A contact_email 400 (R2) gets the exact same banner item and
      // wording as the client-side format/required check in handleSubmit,
      // not extractErrorMessage's generic top line — the banner keeps its
      // usual heading either way, see contactEmailServerError's own
      // comment.
      const contactEmailInvalid = contactEmailServerError(apiError.details);

      // Prefer the server's specific reason (e.g. "This attendee doesn't
      // meet this ticket type's age requirements.") — extracted straight
      // from apiError.details rather than apiError.message, since the
      // latter already falls back to the raw HTTP status text
      // (client.ts::extractErrorMessage's own fallback) and that's exactly
      // the non-specific case this must not surface as if it were real
      // information.
      error = contactEmailInvalid
        ? $t('register.errorBannerHeading')
        : extractErrorMessage(apiError.details, '') || $t('register.submitError');

      // Fold a 400 that maps to a specific attendee into the same named,
      // clickable summary the client-side checks above use (increment 5,
      // 2026-09-28) — childAgeError already surfaces the identical message
      // as an inline caption under that child's ticket select; this is the
      // same information, also in the banner. Parent indices in the DRF
      // error body are positions in the submitted payload.parents array
      // (only named parents are sent, see validParentEntries in
      // handleSubmit), not positions in the full `parents` state array, so
      // this re-derives that same filtered order rather than indexing
      // `parents` directly.
      const parentEntries = parents
        .map((p, index) => ({ p, index }))
        .filter(({ p }) => p.first_name.trim().length > 0);
      const serverProblems: SubmitProblem[] = [];
      if (contactEmailInvalid) {
        serverProblems.push({
          id: 'contact-email',
          message: $t('register.contactEmailRequired'),
          focusSelector: '#contact-email'
        });
      }
      parentEntries.forEach(({ p, index }, payloadIndex) => {
        const fieldMessage = extractFieldError(apiError.details, 'parents', payloadIndex);
        if (fieldMessage) {
          serverProblems.push({
            id: `server-parent-${index}`,
            message: $t('register.fieldErrorNamed', {
              values: { name: parentAttendeeLabel(p, index), message: fieldMessage }
            }),
            focusSelector: `[data-testid="parent-ticket-type-${index}"]`
          });
        }
      });
      children.forEach((child, index) => {
        const fieldMessage = extractFieldError(apiError.details, 'children', index);
        if (fieldMessage) {
          serverProblems.push({
            id: `server-child-${index}`,
            message: $t('register.fieldErrorNamed', {
              values: { name: childAttendeeLabel(child, index), message: fieldMessage }
            }),
            focusSelector: `[data-testid="child-ticket-type-${index}"]`
          });
        }
      });
      submitProblems = serverProblems;
    } finally {
      submitting = false;
    }
  }

  // Recovery action for the idempotency-conflict guidance banner — see
  // idempotencyConflictPayload's own comment for the "lost response" case
  // this exists for. A fresh key, not a retry of the rejected one: the
  // guardian is explicitly told their previous attempt may have already
  // gone through and is choosing to try again anyway, which is exactly
  // "starts a new registration" per idempotencyKey's own reset rule (see
  // handleEditEmail).
  //
  // Inherited, not fixed here: if the original registration this conflict
  // points at was already verified, or has since expired, this resubmit
  // creates a genuine second registration rather than being caught by any
  // dedup — there is no way to know, client-side, whether the original
  // attempt is still "live". handleResend above has the identical edge for
  // the identical reason (see its own docstring) — this isn't a new gap,
  // just the same one reached from a different button.
  async function handleResubmitAfterConflict() {
    if (!idempotencyConflictPayload || submitting) return;
    idempotencyKey = crypto.randomUUID();
    const payload = { ...idempotencyConflictPayload, idempotency_key: idempotencyKey };
    await submitPayload(payload);
  }

  // Resends to the SAME address the original submission used — never a
  // caller-supplied address. Deliberately reuses submit_registration's
  // existing (event, contact_email)-pending dedup path (fresh token,
  // 10-minute cooldown, same RegistrationSubmitThrottle) rather than adding
  // a new "resend by reference code/registration id" endpoint: that shape
  // would let anyone who lands on this public confirmation screen (or
  // guesses/observes a reference code) redirect a stranger's registration
  // to an address they control. This is the safe subset — see report.
  async function handleResend() {
    if (!lastSubmitPayload || resending) return;
    resending = true;
    resendStatus = null;
    try {
      // Strip idempotency_key rather than reuse it — see the comment on
      // lastSubmitPayload's assignment in handleSubmit above. Omitting it
      // entirely (not just regenerating one) is the deliberate choice: it
      // falls straight back to the pre-existing (event, contact_email)
      // dedup+resend path this function's own docstring already describes,
      // unchanged, rather than adding a second, less-tested way to reach
      // the same resend behavior.
      const { idempotency_key: _idempotencyKey, ...resendPayload } = lastSubmitPayload;
      const response = await registrationApi.submit(resendPayload);
      // Whether the backend actually re-sent or short-circuited on its own
      // cooldown, a confirmation email was sent to this address recently
      // either way — same advice to the guardian in both cases, so there's
      // no need to parse the (unlocalized) response message to tell them apart.
      // An explicit email_sent:false is the exception: the send was tried and
      // failed, so saying "sent" would be a lie.
      const delivered = response.email_sent !== false;
      resendStatus = delivered ? 'sent' : 'error';
      emailSent = delivered;
    } catch (err) {
      console.error('Resend failed:', err);
      resendStatus = 'error';
    } finally {
      resending = false;
    }
  }

  // Drops back into the form, still populated with everything already
  // entered, so a mistyped contact email can be corrected and resubmitted
  // without re-keying the whole registration.
  function handleEditEmail() {
    submitted = false;
    // Also reached from the pendingDuplicate screen's own back button (same
    // "drop back into the still-populated form" action) — clear it here too
    // so a subsequent submit is judged fresh rather than re-rendering the
    // stale pending-duplicate state before the new response comes back.
    pendingDuplicate = null;
    resendStatus = null;
    // A fresh idempotency key: the guardian is about to change at least
    // the contact email and submit again, which is a genuinely different
    // payload from the one idempotencyKey was already used for — reusing
    // it would make the backend see "same key, different payload" and
    // reject the correction as a conflict instead of accepting it (see
    // idempotencyKey's own comment above for why this is the one reset
    // point in this flow).
    idempotencyKey = crypto.randomUUID();
  }
</script>

<svelte:head>
  <title>{eventInfo ? $t('register.pageTitle', { values: { event: eventInfo.name } }) : $t('register.heading', { values: { event: '' } })}</title>
</svelte:head>

<main class="container mx-auto p-6 max-w-2xl">
  {#if loadingEvent}
    <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center text-neutral-600">
      {$t('register.loadingEvent')}
    </div>
  {:else if eventNotFound || !eventInfo}
    <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center">
      <p class="text-danger-700 font-semibold">{$t('register.eventNotFound')}</p>
    </div>
  {:else if !isPreview && eventInfo.registration_window_status === 'not_open_yet'}
    <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center" data-testid="register-not-open-yet">
      <h1 class="text-xl font-bold text-neutral-900 mb-2">{$t('register.notOpenYetTitle')}</h1>
      <p class="text-neutral-700">
        {$t('register.notOpenYetMessage', {
          values: {
            event: eventInfo.name,
            date: eventInfo.registration_opens_at ? formatDateTime(eventInfo.registration_opens_at) : ''
          }
        })}
      </p>
    </div>
  {:else if !isPreview && eventInfo.registration_window_status === 'closed'}
    <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center" data-testid="register-closed">
      <h1 class="text-xl font-bold text-neutral-900 mb-2">{$t('register.closedTitle')}</h1>
      <p class="text-neutral-700">
        {$t('register.closedMessage', {
          values: {
            event: eventInfo.name,
            date: eventInfo.registration_closes_at ? formatDateTime(eventInfo.registration_closes_at) : ''
          }
        })}
      </p>
    </div>
  {:else if !isPreview && eventInfo.registration_window_status === 'not_configured'}
    <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center" data-testid="register-not-configured">
      <h1 class="text-xl font-bold text-neutral-900 mb-2">{$t('register.notConfiguredTitle')}</h1>
      <p class="text-neutral-700">{$t('register.notConfiguredMessage')}</p>
    </div>
  {:else if pendingDuplicate}
    <!--
      Dedicated screen (not the ordinary success screen) for the backend's
      "registration_already_pending" code — see pendingDuplicate's own
      comment above. Deliberately does NOT reuse the successTitle/success
      markup: that screen's whole point is "you're done, check your email",
      and this is the opposite message — nothing from this submission was
      saved, the ORIGINAL pending registration is untouched, and the way
      forward is either the email already on its way to the guardian or the
      event organizer, not this page.
    -->
    <div
      class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center"
      data-testid="register-pending-duplicate"
    >
      <h1 class="text-2xl font-bold text-neutral-900 mb-3">
        {$t('register.pendingDuplicateTitle')}
      </h1>
      <Alert type="warning">
        <p class="text-left">
          {$t('register.pendingDuplicateMessage', {
            values: { email: contactEmail.trim() }
          })}
        </p>
        <p class="text-left mt-2">
          {pendingDuplicate.emailResent
            ? $t('register.pendingDuplicateEmailResent')
            : $t('register.pendingDuplicateUseExisting')}
        </p>
        <p class="text-left mt-2">{$t('register.pendingDuplicateContactOrganizer')}</p>
      </Alert>

      {#if pendingDuplicate.referenceCode}
        <p class="text-sm text-neutral-500 mt-4" data-testid="register-pending-duplicate-reference">
          {$t('register.referenceCode', { values: { code: pendingDuplicate.referenceCode } })}
        </p>
      {/if}

      <div class="mt-4">
        <Button variant="secondary" size="sm" onclick={handleEditEmail}>
          {$t('register.editEmailButton')}
        </Button>
      </div>
    </div>
  {:else if submitted}
    <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center">
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.successTitle')}</h1>
      <p class="text-neutral-700 mb-3">
        {emailSent ? $t('register.successIntro') : $t('register.successIntroNotSent')}
      </p>

      <div
        class="inline-flex items-center gap-2 px-4 py-2 mb-3 bg-primary-50 border border-primary-200 rounded-card"
        data-testid="register-success-email"
      >
        <Icon name="mail" size="sm" class="text-primary-600 shrink-0" />
        <span class="font-semibold text-neutral-900 break-all">{contactEmail.trim()}</span>
      </div>

      {#if emailSent}
        <p class="text-sm text-neutral-600 mb-4">{$t('register.successHint')}</p>
      {:else}
        <p
          class="text-sm text-warning-800 bg-warning-50 border border-warning-200 rounded-card px-4 py-3 mb-4 text-left"
          role="status"
          data-testid="register-email-not-sent"
        >
          {$t('register.emailNotSent')}
        </p>
      {/if}

      {#if referenceCode}
        <p class="text-sm text-neutral-500 mb-4">
          {$t('register.referenceCode', { values: { code: referenceCode } })}
        </p>
      {/if}

      <div class="flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-3">
        <Button
          variant="secondary"
          size="sm"
          loading={resending}
          disabled={resending}
          onclick={handleResend}
        >
          {resending ? $t('register.resending') : $t('register.resendButton')}
        </Button>
        <span class="text-sm text-neutral-500">
          {$t('register.wrongEmailPrompt')}
          <button
            type="button"
            class="text-primary-600 hover:text-primary-700 hover:underline font-medium"
            on:click={handleEditEmail}
            data-testid="register-edit-email"
          >
            {$t('register.editEmailButton')}
          </button>
        </span>
      </div>

      {#if resendStatus === 'sent'}
        <p class="mt-3 text-xs text-success-700" data-testid="register-resend-sent">
          {$t('register.resendSent')}
        </p>
      {:else if resendStatus === 'error'}
        <p class="mt-3 text-xs text-danger-700">{$t('register.resendError')}</p>
      {/if}
    </div>
  {:else}
    {#if eventInfo.header_image_url}
      <img
        src={eventInfo.header_image_url}
        alt=""
        class="w-full h-40 object-cover rounded-card border border-neutral-300 mb-4"
      />
    {/if}
    {#if isPreview}
      <div
        class="mb-4 p-3 bg-warning-50 border border-warning-200 rounded text-warning-800 text-sm font-semibold text-center"
        data-testid="register-preview-banner"
      >
        {$t('register.previewBanner')}
      </div>
    {/if}
    <form
      on:submit={handleSubmit}
      novalidate
      class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm"
      data-testid="register-form"
    >
      <!--
        novalidate, deliberately (increment 5, 2026-09-28): a critic caught
        the browser's own validation bubble firing on an empty required
        input before handleSubmit ever ran, pre-empting the page's own
        named error summary below with a generic native tooltip on
        whichever field happened to be first in DOM order. Most of this
        form's "required" is conditional in ways the native constraint
        model can't express anyway — a ticket-type select is only required
        when the event has ticket types, Relation only for a parent row
        that's actually named, a required-choice extra only when the event
        marks it required — so handleSubmit's own checks are the single
        source of truth either way. `required`/`aria-required` stay on the
        fields below for semantics (a screen reader still announces
        "required"), they just no longer block the browser's default submit
        behavior.
      -->
      <EyebrowLabel color={eventInfo.accent_color ?? undefined}>
        {formatDateRange(eventInfo.start_date, eventInfo.end_date)}
      </EyebrowLabel>
      <h1 class="text-2xl font-bold text-neutral-900 mb-1">
        {$t('register.heading', { values: { event: eventInfo.name } })}
      </h1>
      <p class="text-sm text-neutral-600 mb-1">{$t('register.introText')}</p>
      {#if eventInfo.is_paid && eventInfo.price && eventInfo.ticket_types.length === 0}
        <p class="text-sm font-semibold text-neutral-700 mb-4">
          {$t('register.eventPriceNotice', { values: { amount: formatCurrency(eventInfo.price), currency: eventInfo.currency } })}
        </p>
      {/if}

      <p class="text-xs text-neutral-500 mb-4" data-testid="register-required-legend">
        <span class="text-danger-600" aria-hidden="true">*</span> {$t('register.requiredFieldLegend')}
      </p>

      {#if error || submitProblems.length > 0}
        <!--
          R4 (registration dev-cycle round 4, increment 5 revision): reuses
          the shared Alert primitive (type="error" — this codebase's danger
          variant) for the same bg-danger-50/border-danger-200 tokens this
          banner already used by hand, and drops the aria-live this block
          used to carry alongside role="alert" (Alert itself sets role=
          "alert" — the pairing double-announces to a screen reader, one
          for the live-region mutation and one for the role, so aria-live
          is redundant here and everywhere else on this page that already
          pairs role="alert" alone). Alert has no ref/tabindex passthrough,
          so the outer div (same pattern as idempotencyConflictBannerEl
          below) is still what the scroll/focus $effect targets.
        -->
        <div
          class="mb-4 rounded-card focus:outline-none focus:ring-2 focus:ring-danger-500"
          tabindex="-1"
          bind:this={errorBannerEl}
          data-testid="register-error-banner"
        >
          <Alert type="error">
            {#if error}
              <p class={submitProblems.length > 0 ? 'font-semibold mb-2' : ''}>{error}</p>
            {/if}
            {#if submitProblems.length > 0}
              <ul class="space-y-1 pl-0 list-none">
                {#each submitProblems as problem (problem.id)}
                  <li>
                    {#if problem.focusSelector}
                      <button
                        type="button"
                        class="text-left underline decoration-danger-400 hover:decoration-danger-700 focus:outline-none focus:ring-2 focus:ring-danger-500 rounded"
                        on:click={() => focusOnProblem(problem)}
                        data-testid={`register-error-item-${problem.id}`}
                      >
                        {problem.message}
                      </button>
                    {:else}
                      <span data-testid={`register-error-item-${problem.id}`}>{problem.message}</span>
                    {/if}
                  </li>
                {/each}
              </ul>
            {/if}
          </Alert>
        </div>
      {/if}

      {#if idempotencyConflictPayload}
        <!--
          Guidance, not a red error — the registration may already exist,
          so `info` (not `danger`) is the deliberate semantic choice here
          (see the design-system rule: danger is for something that failed,
          this is "we're not sure, check before retrying"). The outer div
          (not Alert.svelte itself, which has no ref/tabindex passthrough)
          is what the scroll/focus effect above targets.
        -->
        <div class="mb-4" tabindex="-1" bind:this={idempotencyConflictBannerEl}>
          <Alert type="info" title={$t('register.idempotencyConflictTitle')}>
            <p>
              {$t('register.idempotencyConflictMessage', {
                values: { email: contactEmail.trim() }
              })}
            </p>
            <div class="mt-3">
              <Button
                variant="secondary"
                size="sm"
                loading={submitting}
                disabled={submitting}
                onclick={handleResubmitAfterConflict}
              >
                {$t('register.idempotencyConflictButton')}
              </Button>
            </div>
          </Alert>
        </div>
      {/if}

      <!--
        Honeypot field: visually hidden, never shown to real users. `inert`
        (not just aria-hidden) is what actually keeps it out of the
        accessibility tree here — aria-hidden alone on a container with a
        focusable descendant is an invalid combination per the ARIA spec,
        and some assistive tech still surfaces the field to screen-reader
        users despite aria-hidden, which is exactly the trap this exists to
        avoid. `inert` makes the field genuinely non-focusable/non-
        interactive for real users while a naive spam bot — which fills
        form fields by name without respecting focus or ARIA state — still
        finds and fills it.
      -->
      <div class="absolute -left-[9999px]" aria-hidden="true" inert>
        <label for="website">Website</label>
        <input
          id="website"
          name="website"
          type="text"
          tabindex="-1"
          autocomplete="off"
          bind:value={website}
        />
      </div>

      <div class="mb-4">
        <label for="contact-email" class="block text-sm font-semibold text-neutral-700 mb-1">
          {$t('register.contactEmail')} <span class="text-danger-600" aria-hidden="true">*</span>
        </label>
        <input
          id="contact-email"
          type="email"
          bind:value={contactEmail}
          on:input={() => clearSubmitProblem('contact-email')}
          placeholder={$t('register.contactEmailPlaceholder')}
          required
          aria-required="true"
          maxlength="254"
          aria-invalid={hasProblem('contact-email') ? 'true' : 'false'}
          class={`w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 ${
            hasProblem('contact-email')
              ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
              : 'border-neutral-300 focus:ring-primary-500'
          }`}
          data-testid="register-contact-email"
        />
        <p class="text-xs text-neutral-500 mt-1">{$t('register.contactEmailHelp')}</p>
      </div>

      <div class="mb-4">
        <label for="family-name" class="block text-sm font-semibold text-neutral-700 mb-1">
          {$t('checkin.familyName')}:
        </label>
        <input
          id="family-name"
          type="text"
          bind:value={familyName}
          placeholder={$t('checkin.familyNamePlaceholder')}
          maxlength="255"
          class="w-full px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      <div class="mb-4">
        <div class="block text-sm font-semibold text-neutral-700 mb-2">
          {$t('checkin.parentInfo')}:
        </div>
        <div class="space-y-3">
          {#each parents as parent, index (index)}
            <div class="border border-neutral-200 rounded p-3 bg-neutral-50">
              <div class="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <label for={`parent-first-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                    <!--
                      No required star here, deliberately (R1, registration
                      dev-cycle round 4, increment 5 revision) — see
                      validParents' own comment in handleSubmit above. This
                      row is silently dropped, not required, if left blank;
                      a star here would promise an enforcement this form
                      doesn't have.
                    -->
                    {$t('checkin.parentFirstName')}
                  </label>
                  <input
                    id={`parent-first-name-${index}`}
                    type="text"
                    bind:value={parent.first_name}
                    placeholder={$t('checkin.parentFirstNamePlaceholder')}
                    maxlength="255"
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label for={`parent-last-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.parentLastName')}
                  </label>
                  <input
                    id={`parent-last-name-${index}`}
                    type="text"
                    bind:value={parent.last_name}
                    placeholder={$t('checkin.parentLastNamePlaceholder')}
                    maxlength="255"
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <label for={`parent-relationship-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.relationshipType')} <span class="text-danger-600" aria-hidden="true">*</span>
                  </label>
                  <select
                    id={`parent-relationship-${index}`}
                    bind:value={parent.relationship_type}
                    required
                    aria-required="true"
                    aria-invalid={relationshipMissing(parent) ? 'true' : 'false'}
                    aria-describedby={relationshipMissing(parent)
                      ? `parent-relationship-missing-${index}`
                      : undefined}
                    class={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 ${
                      relationshipMissing(parent)
                        ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                        : 'border-neutral-300 focus:ring-primary-500'
                    }`}
                    data-testid={`parent-relationship-${index}`}
                  >
                    <option value="">{$t('register.relationshipPlaceholder')}</option>
                    <option value="MOM">{$t('checkin.relationshipMom')}</option>
                    <option value="DAD">{$t('checkin.relationshipDad')}</option>
                    <option value="GUARDIAN">{$t('checkin.relationshipGuardian')}</option>
                    <option value="OTHER">{$t('checkin.relationshipOther')}</option>
                  </select>
                  {#if relationshipMissing(parent)}
                    <p
                      id={`parent-relationship-missing-${index}`}
                      class="mt-1 text-xs text-danger-700"
                      role="alert"
                      data-testid={`parent-relationship-missing-${index}`}
                    >
                      {$t('register.relationshipRequiredCaption')}
                    </p>
                  {/if}
                </div>
                <div>
                  <label for={`parent-phone-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.parentPhone')}
                  </label>
                  <input
                    id={`parent-phone-${index}`}
                    type="tel"
                    bind:value={parent.phone}
                    on:input={() => clearSubmitProblem(`parent-phone-${index}`)}
                    placeholder={$t('checkin.parentPhonePlaceholder')}
                    maxlength="50"
                    aria-invalid={hasProblem(`parent-phone-${index}`) ? 'true' : 'false'}
                    class={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 ${
                      hasProblem(`parent-phone-${index}`)
                        ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                        : 'border-neutral-300 focus:ring-primary-500'
                    }`}
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label for={`parent-email-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.parentEmail')}
                  </label>
                  <input
                    id={`parent-email-${index}`}
                    type="email"
                    bind:value={parent.email}
                    placeholder={$t('checkin.parentEmailPlaceholder')}
                    maxlength="254"
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              {#if applicableTicketTypes(false).length > 0}
                <div class="mt-2">
                  <label for={`parent-ticket-type-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('register.ticketTypeLabel')} <span class="text-danger-600" aria-hidden="true">*</span>
                  </label>
                  <select
                    id={`parent-ticket-type-${index}`}
                    value={parent.ticketTypeId}
                    on:change={(e) =>
                      handleParentTicketTypeChange(index, (e.currentTarget as HTMLSelectElement).value)}
                    required
                    aria-required="true"
                    aria-invalid={ticketCompositionWarning(parent.ticketTypeId) !== null ||
                    ticketSoldOutWarning(parent.ticketTypeId) !== null ||
                    hasProblem(`parent-ticket-type-${index}`)
                      ? 'true'
                      : 'false'}
                    aria-describedby={[
                      ticketCompositionWarning(parent.ticketTypeId) !== null
                        ? `parent-ticket-composition-${index}`
                        : null,
                      ticketSoldOutWarning(parent.ticketTypeId) !== null
                        ? `parent-ticket-sold-out-${index}`
                        : null,
                      parent.promoReset ? `parent-ticket-promo-reset-${index}` : null
                    ]
                      .filter(Boolean)
                      .join(' ') || undefined}
                    class={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 ${
                      ticketCompositionWarning(parent.ticketTypeId) !== null ||
                      ticketSoldOutWarning(parent.ticketTypeId) !== null ||
                      hasProblem(`parent-ticket-type-${index}`)
                        ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                        : 'border-neutral-300 focus:ring-primary-500'
                    }`}
                    data-testid={`parent-ticket-type-${index}`}
                  >
                    <option value="" selected={parent.ticketTypeId === ''}>
                      {$t('register.ticketTypePlaceholder')}
                    </option>
                    {#each applicableTicketTypes(false) as ticketType (ticketType.id)}
                      <option
                        value={ticketType.id}
                        selected={ticketType.id === parent.ticketTypeId}
                        disabled={!ticketCompositionEligible(ticketType, ticketType.id === parent.ticketTypeId) ||
                          !ticketAvailable(ticketType, ticketType.id === parent.ticketTypeId)}
                      >
                        {ticketOptionLabel(ticketType, '', ticketType.id === parent.ticketTypeId)}
                      </option>
                    {/each}
                  </select>
                  {#if ticketCompositionWarning(parent.ticketTypeId)}
                    <p
                      id={`parent-ticket-composition-${index}`}
                      class="mt-1 text-xs text-danger-700"
                      role="alert"
                      data-testid={`parent-ticket-composition-${index}`}
                    >
                      {ticketCompositionWarning(parent.ticketTypeId)}
                    </p>
                  {/if}
                  {#if ticketSoldOutWarning(parent.ticketTypeId)}
                    <p
                      id={`parent-ticket-sold-out-${index}`}
                      class="mt-1 text-xs text-danger-700"
                      role="alert"
                      data-testid={`parent-ticket-sold-out-${index}`}
                    >
                      {ticketSoldOutWarning(parent.ticketTypeId)}
                    </p>
                  {/if}
                  {#if parent.promoReset}
                    <p
                      id={`parent-ticket-promo-reset-${index}`}
                      class="mt-1 text-xs text-neutral-600"
                      data-testid={`parent-ticket-promo-reset-${index}`}
                    >
                      {$t('register.promoResetCaption')}
                    </p>
                  {/if}
                </div>
              {/if}

              {#each applicablePersonExtras(false).filter((extra) => extra.required) as extra (extra.id)}
                {@const state = extraState(parent.extraSelections, extra)}
                {#if extra.requires_choice}
                  <fieldset
                    class={`mt-2 min-w-0 ${
                      hasProblem(`parent-extra-${extra.id}-${index}`)
                        ? 'border border-danger-600 rounded-card p-2'
                        : 'border-0 p-0 m-0'
                    }`}
                    data-testid={`parent-extra-required-${extra.id}-${index}`}
                  >
                    <legend class="block text-xs text-neutral-600 mb-1 p-0">
                      {extra.name}
                      {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''}
                      <span class="text-danger-600" aria-hidden="true">*</span>
                    </legend>
                    <div class="flex items-center gap-3 flex-wrap">
                      {#each extra.choices as choice (choice.id)}
                        <label class="flex items-center gap-1 text-sm text-neutral-700">
                          <input
                            type="radio"
                            name={`extra-${extra.id}-parent-${index}`}
                            checked={state.choiceId === choice.id}
                            required
                            on:change={() => {
                              setExtraChoice(parent.extraSelections, extra, choice.id);
                              clearSubmitProblem(`parent-extra-${extra.id}-${index}`);
                            }}
                          />
                          {choice.label}{choice.price_delta !== '0.00' ? ` (+${formatCurrency(choice.price_delta)} kr)` : ''}
                        </label>
                      {/each}
                    </div>
                  </fieldset>
                {:else}
                  <div class="mt-2">
                    <div class="block text-xs text-neutral-600 mb-1">
                      {extra.name} {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''}
                      <span class="text-danger-600" aria-hidden="true">*</span>
                    </div>
                  </div>
                {/if}
              {/each}

              {#if applicablePersonExtras(false).filter((extra) => !extra.required).length > 0}
                <div class="mt-2 space-y-1.5">
                  <div class="block text-xs text-neutral-600">{$t('register.extrasLabel')}</div>
                  {#each applicablePersonExtras(false).filter((extra) => !extra.required) as extra (extra.id)}
                    {@const state = extraState(parent.extraSelections, extra)}
                    <div class="flex items-center gap-2 flex-wrap">
                      <label class="flex items-center gap-1.5 text-sm text-neutral-700">
                        <input
                          type="checkbox"
                          checked={state.selected}
                          on:change={(e) =>
                            setExtraSelected(
                              parent.extraSelections,
                              extra,
                              (e.currentTarget as HTMLInputElement).checked
                            )}
                        />
                        {extra.name} ({formatCurrency(extra.price)} kr)
                      </label>
                      {#if extra.requires_choice && state.selected}
                        <select
                          value={state.choiceId}
                          on:change={(e) =>
                            setExtraChoice(
                              parent.extraSelections,
                              extra,
                              (e.currentTarget as HTMLSelectElement).value
                            )}
                          class="px-2 py-1 text-sm border border-neutral-300 rounded"
                        >
                          <option value="">{$t('register.extraChoicePlaceholder')}</option>
                          {#each extra.choices as choice (choice.id)}
                            <option value={choice.id}>{choice.label}</option>
                          {/each}
                        </select>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}

              <div class="mt-2">
                <ConsentCapture
                  bind:status={parent.healthInfoStatus}
                  bind:allergies={parent.allergies}
                  bind:notes={parent.notes}
                  bind:consentNoticeShared={parent.consentNoticeShared}
                  idPrefix={`parent-${index}`}
                  testIdPrefix="parent"
                  attestLabelKey="register.consentAttest"
                  questionKey="register.adultHealthInfoQuestion"
                  consentLabelKey="register.adultHealthInfoConsent"
                  declineLabelKey="register.adultHealthInfoDecline"
                  noticeKey="register.adultHealthConsentNotice"
                  declinedNoteKey="register.adultHealthInfoDeclinedNote"
                  noticeLinkHref="/privacy"
                />
              </div>

              {#if parents.length > 1}
                <button
                  type="button"
                  on:click={() => handleRemoveParent(index)}
                  class="mt-2 text-danger-600 hover:text-danger-700 text-xs font-medium"
                >
                  {$t('checkin.removeParent')}
                </button>
              {/if}
            </div>
          {/each}
        </div>
        <button
          type="button"
          on:click={handleAddParent}
          class="mt-2 text-primary-600 hover:text-primary-700 text-sm font-semibold"
        >
          + {$t('checkin.addParent')}
        </button>
      </div>

      <div class="mb-4">
        <div class="block text-sm font-semibold text-neutral-700 mb-2">
          {$t('checkin.children')}:
        </div>
        <div class="space-y-3">
          {#each children as child, index (index)}
            <div class="border border-neutral-200 rounded p-3 bg-neutral-50">
              <div class="flex justify-between items-center mb-2">
                <span class="text-sm font-semibold text-neutral-700">
                  {$t('checkin.childNumber', { values: { number: index + 1 } })}
                </span>
                {#if children.length > 1}
                  <button
                    type="button"
                    on:click={() => handleRemoveChild(index)}
                    class="text-danger-600 hover:text-danger-700 text-xs font-medium"
                  >
                    {$t('checkin.removeChild')}
                  </button>
                {/if}
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div>
                  <label for={`child-first-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.childFirstName')} <span class="text-danger-600" aria-hidden="true">*</span>
                  </label>
                  <input
                    id={`child-first-name-${index}`}
                    type="text"
                    bind:value={child.first_name}
                    on:input={() => clearSubmitProblem(`child-info-${index}`)}
                    placeholder={$t('checkin.childFirstNamePlaceholder')}
                    maxlength="255"
                    aria-invalid={hasProblem(`child-info-${index}`) ? 'true' : 'false'}
                    class={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 ${
                      hasProblem(`child-info-${index}`)
                        ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                        : 'border-neutral-300 focus:ring-primary-500'
                    }`}
                    required
                  />
                </div>

                <div>
                  <label for={`child-last-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.childLastName')} <span class="text-danger-600" aria-hidden="true">*</span>
                  </label>
                  <input
                    id={`child-last-name-${index}`}
                    type="text"
                    bind:value={child.last_name}
                    on:input={() => clearSubmitProblem(`child-info-${index}`)}
                    placeholder={$t('checkin.childLastNamePlaceholder')}
                    maxlength="255"
                    aria-invalid={hasProblem(`child-info-${index}`) ? 'true' : 'false'}
                    class={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 ${
                      hasProblem(`child-info-${index}`)
                        ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                        : 'border-neutral-300 focus:ring-primary-500'
                    }`}
                    required
                  />
                </div>

                <div>
                  <label for={`child-birthdate-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.childBirthdate')} <span class="text-danger-600" aria-hidden="true">*</span>
                  </label>
                  <input
                    id={`child-birthdate-${index}`}
                    type="date"
                    bind:value={child.birthdate}
                    on:change={(e) => {
                      handleChildBirthdateChange(child, e);
                      clearSubmitProblem(`child-info-${index}`);
                    }}
                    lang={$locale === 'sv' ? 'sv-SE' : 'en-US'}
                    max={todayIso}
                    min={minBirthdateIso}
                    aria-invalid={child.birthdateRangeInvalid || hasProblem(`child-info-${index}`)
                      ? 'true'
                      : 'false'}
                    aria-describedby={child.birthdateRangeInvalid
                      ? `child-birthdate-invalid-${index}`
                      : undefined}
                    class={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 ${
                      child.birthdateRangeInvalid || hasProblem(`child-info-${index}`)
                        ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                        : 'border-neutral-300 focus:ring-primary-500'
                    }`}
                    required
                  />
                  <p class="mt-1 text-xs text-neutral-500">{$t('register.birthdateFormatHint')}</p>
                  {#if child.birthdateRangeInvalid}
                    <p
                      id={`child-birthdate-invalid-${index}`}
                      class="mt-1 text-xs font-medium text-danger-700"
                      role="alert"
                      data-testid={`child-birthdate-invalid-${index}`}
                    >
                      {$t('register.birthdateInvalid')}
                    </p>
                  {:else if birthdateProse(child.birthdate)}
                    <p
                      class="mt-1 text-xs font-medium text-neutral-700"
                      data-testid={`child-birthdate-prose-${index}`}
                    >
                      {birthdateProse(child.birthdate)}
                    </p>
                  {/if}
                </div>

                {#if applicableTicketTypes(true).length > 0}
                  <div>
                    <label for={`child-ticket-type-${index}`} class="block text-xs text-neutral-600 mb-1">
                      {$t('register.ticketTypeLabel')} <span class="text-danger-600" aria-hidden="true">*</span>
                    </label>
                    <select
                      id={`child-ticket-type-${index}`}
                      value={child.ticketTypeId}
                      on:change={(e) =>
                        handleChildTicketTypeChange(index, (e.currentTarget as HTMLSelectElement).value)}
                      required
                      aria-required="true"
                      aria-invalid={childSelectedTicketWarning(child) !== null ||
                      ticketCompositionWarning(child.ticketTypeId) !== null ||
                      ticketSoldOutWarning(child.ticketTypeId) !== null ||
                      hasProblem(`child-ticket-type-${index}`)
                        ? 'true'
                        : 'false'}
                      aria-describedby={childTicketDescribedBy(index, child)}
                      class={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 ${
                        childSelectedTicketWarning(child) !== null ||
                        ticketCompositionWarning(child.ticketTypeId) !== null ||
                        ticketSoldOutWarning(child.ticketTypeId) !== null ||
                        hasProblem(`child-ticket-type-${index}`)
                          ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                          : 'border-neutral-300 focus:ring-primary-500'
                      }`}
                      data-testid={`child-ticket-type-${index}`}
                    >
                      <option value="" selected={child.ticketTypeId === ''}>
                        {$t('register.ticketTypePlaceholder')}
                      </option>
                      {#each applicableTicketTypes(true) as ticketType (ticketType.id)}
                        <option
                          value={ticketType.id}
                          selected={ticketType.id === child.ticketTypeId}
                          disabled={!childTicketEligible(ticketType, child.birthdate) ||
                            !ticketCompositionEligible(ticketType, ticketType.id === child.ticketTypeId) ||
                            !ticketAvailable(ticketType, ticketType.id === child.ticketTypeId)}
                        >
                          {ticketOptionLabel(ticketType, child.birthdate, ticketType.id === child.ticketTypeId)}
                        </option>
                      {/each}
                    </select>
                    {#if childSelectedTicketWarning(child)}
                      <p
                        id={`child-ticket-ineligible-${index}`}
                        class="mt-1 text-xs text-danger-700"
                        role="alert"
                        data-testid={`child-ticket-ineligible-${index}`}
                      >
                        {childSelectedTicketWarning(child)}
                      </p>
                    {/if}
                    {#if ticketCompositionWarning(child.ticketTypeId)}
                      <p
                        id={`child-ticket-composition-${index}`}
                        class="mt-1 text-xs text-danger-700"
                        role="alert"
                        data-testid={`child-ticket-composition-${index}`}
                      >
                        {ticketCompositionWarning(child.ticketTypeId)}
                      </p>
                    {/if}
                    {#if ticketSoldOutWarning(child.ticketTypeId)}
                      <p
                        id={`child-ticket-sold-out-${index}`}
                        class="mt-1 text-xs text-danger-700"
                        role="alert"
                        data-testid={`child-ticket-sold-out-${index}`}
                      >
                        {ticketSoldOutWarning(child.ticketTypeId)}
                      </p>
                    {/if}
                    {#if childAgeError(index)}
                      <p class="mt-1 text-xs text-danger-700" data-testid={`child-age-error-${index}`}>
                        {childAgeError(index)}
                      </p>
                    {/if}
                    {#if child.promoReset}
                      <p
                        id={`child-ticket-promo-reset-${index}`}
                        class="mt-1 text-xs text-neutral-600"
                        data-testid={`child-ticket-promo-reset-${index}`}
                      >
                        {$t('register.promoResetCaption')}
                      </p>
                    {/if}
                  </div>
                {/if}

                {#each applicablePersonExtras(true).filter((extra) => extra.required) as extra (extra.id)}
                  {@const state = extraState(child.extraSelections, extra)}
                  {#if extra.requires_choice}
                    <fieldset
                      class={`md:col-span-2 min-w-0 ${
                        hasProblem(`child-extra-${extra.id}-${index}`)
                          ? 'border border-danger-600 rounded-card p-2'
                          : 'border-0 p-0 m-0'
                      }`}
                      data-testid={`child-extra-required-${extra.id}-${index}`}
                    >
                      <legend class="block text-xs text-neutral-600 mb-1 p-0">
                        {extra.name}
                        {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''}
                        <span class="text-danger-600" aria-hidden="true">*</span>
                      </legend>
                      <div class="flex items-center gap-3 flex-wrap">
                        {#each extra.choices as choice (choice.id)}
                          <label class="flex items-center gap-1 text-sm text-neutral-700">
                            <input
                              type="radio"
                              name={`extra-${extra.id}-child-${index}`}
                              checked={state.choiceId === choice.id}
                              required
                              on:change={() => {
                                setExtraChoice(child.extraSelections, extra, choice.id);
                                clearSubmitProblem(`child-extra-${extra.id}-${index}`);
                              }}
                            />
                            {choice.label}{choice.price_delta !== '0.00' ? ` (+${formatCurrency(choice.price_delta)} kr)` : ''}
                          </label>
                        {/each}
                      </div>
                    </fieldset>
                  {:else}
                    <div class="md:col-span-2">
                      <div class="block text-xs text-neutral-600 mb-1">
                        {extra.name} {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''}
                        <span class="text-danger-600" aria-hidden="true">*</span>
                      </div>
                    </div>
                  {/if}
                {/each}

                {#if applicablePersonExtras(true).filter((extra) => !extra.required).length > 0}
                  <div class="md:col-span-2 space-y-1.5">
                    <div class="block text-xs text-neutral-600">{$t('register.extrasLabel')}</div>
                    {#each applicablePersonExtras(true).filter((extra) => !extra.required) as extra (extra.id)}
                      {@const state = extraState(child.extraSelections, extra)}
                      <div class="flex items-center gap-2 flex-wrap">
                        <label class="flex items-center gap-1.5 text-sm text-neutral-700">
                          <input
                            type="checkbox"
                            checked={state.selected}
                            on:change={(e) =>
                              setExtraSelected(
                                child.extraSelections,
                                extra,
                                (e.currentTarget as HTMLInputElement).checked
                              )}
                          />
                          {extra.name} ({formatCurrency(extra.price)} kr)
                        </label>
                        {#if extra.requires_choice && state.selected}
                          <select
                            value={state.choiceId}
                            on:change={(e) =>
                              setExtraChoice(
                                child.extraSelections,
                                extra,
                                (e.currentTarget as HTMLSelectElement).value
                              )}
                            class="px-2 py-1 text-sm border border-neutral-300 rounded"
                          >
                            <option value="">{$t('register.extraChoicePlaceholder')}</option>
                            {#each extra.choices as choice (choice.id)}
                              <option value={choice.id}>{choice.label}</option>
                            {/each}
                          </select>
                        {/if}
                      </div>
                    {/each}
                  </div>
                {/if}

                <div class="md:col-span-2">
                  <ConsentCapture
                    bind:status={child.healthInfoStatus}
                    bind:allergies={child.allergies}
                    bind:notes={child.notes}
                    bind:consentNoticeShared={child.consentNoticeShared}
                    idPrefix={String(index)}
                    attestLabelKey="register.consentAttest"
                  />
                </div>
              </div>
            </div>
          {/each}
        </div>
        <button
          type="button"
          on:click={handleAddChild}
          class="mt-2 text-primary-600 hover:text-primary-700 text-sm font-semibold"
        >
          + {$t('checkin.addAnotherChild')}
        </button>
      </div>

      {#each registrationExtras().filter((extra) => extra.required) as extra (extra.id)}
        {@const state = extraState(registrationExtraSelections, extra)}
        {#if extra.requires_choice}
          <fieldset
            class={`mb-4 min-w-0 ${
              hasProblem(`registration-extra-${extra.id}`)
                ? 'border border-danger-600 rounded-card p-2'
                : 'border-0 p-0 m-0'
            }`}
            data-testid={`registration-extra-required-${extra.id}`}
          >
            <legend class="block text-xs text-neutral-600 mb-1 p-0">
              {extra.name}
              {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''}
              <span class="text-danger-600" aria-hidden="true">*</span>
            </legend>
            <div class="flex items-center gap-3 flex-wrap">
              {#each extra.choices as choice (choice.id)}
                <label class="flex items-center gap-1 text-sm text-neutral-700">
                  <input
                    type="radio"
                    name={`extra-${extra.id}-registration`}
                    checked={state.choiceId === choice.id}
                    required
                    on:change={() => {
                      setExtraChoice(registrationExtraSelections, extra, choice.id);
                      clearSubmitProblem(`registration-extra-${extra.id}`);
                    }}
                  />
                  {choice.label}{choice.price_delta !== '0.00' ? ` (+${formatCurrency(choice.price_delta)} kr)` : ''}
                </label>
              {/each}
            </div>
          </fieldset>
        {:else}
          <div class="mb-4">
            <div class="block text-xs text-neutral-600 mb-1">
              {extra.name} {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''}
              <span class="text-danger-600" aria-hidden="true">*</span>
            </div>
          </div>
        {/if}
      {/each}

      {#if registrationExtras().filter((extra) => !extra.required).length > 0}
        <div class="mb-4">
          <div class="block text-sm font-semibold text-neutral-700 mb-2">
            {$t('register.registrationExtrasHeading')}:
          </div>
          <div class="space-y-2">
            {#each registrationExtras().filter((extra) => !extra.required) as extra (extra.id)}
              {@const state = extraState(registrationExtraSelections, extra)}
              <div class="flex items-center gap-2 flex-wrap border border-neutral-200 rounded p-2 bg-neutral-50">
                <label class="flex items-center gap-1.5 text-sm text-neutral-700">
                  <input
                    type="checkbox"
                    checked={state.selected}
                    on:change={(e) =>
                      setExtraSelected(
                        registrationExtraSelections,
                        extra,
                        (e.currentTarget as HTMLInputElement).checked
                      )}
                  />
                  {extra.name} ({formatCurrency(extra.price)} kr)
                </label>
                {#if extra.requires_choice && state.selected}
                  <select
                    value={state.choiceId}
                    on:change={(e) =>
                      setExtraChoice(
                        registrationExtraSelections,
                        extra,
                        (e.currentTarget as HTMLSelectElement).value
                      )}
                    class="px-2 py-1 text-sm border border-neutral-300 rounded"
                  >
                    <option value="">{$t('register.extraChoicePlaceholder')}</option>
                    {#each extra.choices as choice (choice.id)}
                      <option value={choice.id}>{choice.label}</option>
                    {/each}
                  </select>
                {/if}
                {#if state.selected}
                  <label class="flex items-center gap-1.5 text-sm text-neutral-700">
                    {$t('register.quantityLabel')}
                    <input
                      type="number"
                      min="1"
                      value={state.quantity}
                      on:change={(e) =>
                        setExtraQuantity(
                          registrationExtraSelections,
                          extra,
                          parseInt((e.currentTarget as HTMLInputElement).value, 10) || 1
                        )}
                      class="w-16 px-2 py-1 text-sm border border-neutral-300 rounded"
                    />
                  </label>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if eventInfo.ticket_types.length > 0 || eventInfo.is_paid || eventInfo.has_hidden_ticket_types}
        <div class="mb-4">
          <label for="promo-code-input" class="block text-sm font-semibold text-neutral-700 mb-1">
            {$t('register.promoCodeLabel')}
          </label>
          {#if promoCodeValidation?.valid}
            <!--
              R2 (registration dev-cycle round 4, increment 3 revision): an
              applied code is state, not just a moment — replace the text
              input with a chip so the applied code stays visibly readable
              (and "Ta bort" is the only way to change it) instead of
              silently un-applying the instant the guardian's cursor lands
              back in the box.
            -->
            <div class="flex items-center gap-2 flex-wrap">
              <span
                class="inline-flex items-center gap-1.5 rounded-pill bg-success-50 border border-success-200 px-3 py-1.5 text-sm font-semibold text-success-700"
                data-testid="register-promo-code-chip"
              >
                <Icon name="check-circle" size="sm" class="text-success-600 shrink-0" />
                {promoCodeAppliedValue}
              </span>
              <button
                type="button"
                on:click={handleRemovePromoCode}
                class="inline-flex items-center gap-1 rounded-pill border border-success-300 px-3 py-1.5 text-sm font-semibold text-success-700 hover:bg-success-50"
                data-testid="register-promo-code-remove"
              >
                <Icon name="x" size="sm" class="shrink-0" />
                {$t('register.promoCodeRemoveButton')}
              </button>
            </div>
            <p
              class="mt-1 text-xs text-success-700"
              role="status"
              aria-live="polite"
              data-testid="register-promo-code-applied"
            >
              {promoAppliedMessage()}
            </p>
          {:else}
            <div class="flex items-center gap-2">
              <input
                id="promo-code-input"
                type="text"
                bind:value={promoCode}
                on:input={() => {
                  // Editing the code invalidates whatever "Använd" last
                  // checked — without this, clearing the field leaves the
                  // stale invalid-code message on screen with no way to
                  // dismiss it (Använd stays disabled on an empty field), and
                  // handleSubmit's own guard needs promoCodeValidation to go
                  // stale the instant the text no longer matches what it
                  // validated. retractPromoUnlockedTicketTypes is still
                  // called defensively here (kept from before R2), but in
                  // practice is a no-op by the time this fires: once a code
                  // is applied the input is replaced by the chip above, so
                  // the only way back to this branch is "Ta bort", which
                  // already retracted everything itself (see
                  // handleRemovePromoCode).
                  promoCodeError = '';
                  promoCodeValidation = null;
                  promoCodeAppliedValue = '';
                  promoRemovalMessage = '';
                  retractPromoUnlockedTicketTypes();
                }}
                placeholder={$t('register.promoCodePlaceholder')}
                aria-invalid={promoCodeError ? 'true' : 'false'}
                aria-describedby={promoCodeError ? 'promo-code-error' : undefined}
                class={`flex-1 px-3 py-2 text-sm border rounded-button focus:outline-none focus:ring-2 ${
                  promoCodeError
                    ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
                    : 'border-neutral-300 focus:ring-primary-500'
                }`}
                data-testid="register-promo-code-input"
              />
              <button
                type="button"
                on:click={checkPromoCode}
                disabled={promoCodeChecking || !promoCode.trim()}
                class="px-3 py-2 text-sm font-semibold border border-neutral-300 rounded-button hover:bg-neutral-50 disabled:opacity-50"
                data-testid="register-promo-code-apply"
              >
                {promoCodeChecking ? $t('register.promoCodeChecking') : $t('register.promoCodeApply')}
              </button>
            </div>
            {#if promoCodeError}
              <p
                id="promo-code-error"
                class="mt-1 text-xs text-danger-700"
                role="alert"
                aria-live="polite"
                data-testid="register-promo-code-error"
              >
                {promoCodeError}
              </p>
            {/if}
          {/if}
          {#if promoRemovalMessage}
            <p
              class="mt-1 text-xs text-neutral-600"
              role="status"
              aria-live="polite"
              data-testid="register-promo-removed-message"
            >
              {promoRemovalMessage}
            </p>
          {/if}
        </div>
      {/if}

      {#if eventInfo.ticket_types.length > 0}
        <div class="mb-4 text-right text-sm text-neutral-700" data-testid="register-running-total">
          {#if discountAmount > 0}
            <div class="text-xs font-normal text-neutral-500">
              {$t('register.subtotalLabel')}: {formatCurrency(runningTotal)} kr
            </div>
            <div class="text-xs font-normal text-success-700">
              {$t('register.discountLabel')}: -{formatCurrency(discountAmount)} kr
            </div>
          {/if}
          <div class="font-semibold">
            {$t('register.totalLabel')}: {formatCurrency(discountedTotal)} kr
            {#if hasIneligibleTicketSelection}
              <span class="font-medium text-danger-700" data-testid="register-total-provisional">
                {$t('register.totalProvisional')}
              </span>
            {/if}
          </div>
        </div>
      {/if}

      <div class="flex items-center justify-end gap-3">
        <button
          type="submit"
          disabled={submitting || isPreview}
          aria-busy={submitting}
          title={isPreview ? $t('register.previewSubmitDisabled') : undefined}
          class="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors disabled:opacity-50"
          data-testid="register-submit-button"
        >
          {#if submitting}
            <svg
              class="animate-spin h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              aria-hidden="true"
            >
              <path d="M12 3a9 9 0 1 0 9 9" />
            </svg>
          {/if}
          {submitting ? $t('register.submitting') : $t('register.submitButton')}
        </button>
      </div>
    </form>

    <div class="text-center text-xs text-neutral-500 mt-6">
      {$t('register.privacyNotice')}
      <a href="/privacy" class="text-primary-600 hover:underline">{$t('register.privacyLink')}</a>
    </div>
  {/if}
</main>
