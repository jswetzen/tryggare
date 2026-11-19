# Feature requests from the 2026-11-19 agent UI trial

Product flaws from `2026-11-19-agent-ui-trial.md`, written in the format of `docs/roadmap/feature_requests.md` (phase 0: by hand, no model). Wording is generalised: no names, dates of birth, contact details, event ids or registration contents. Tooling problems (the browser launch) are left out. Duplicates are merged, and requests are ranked by impact: severity first, then reach.

`validator` column: **existing** = a current code catches it; **new warning** = the spec already holds the data, so `_validate.py` could warn today; **no** = needs a model, UI or docs change. Proposed warning codes are marked *(proposed)*.

| Rank | Id | Title | Severity | Layers | Validator |
|---|---|---|---|---|---|
| 1 | FR-1 | An add-on for one age band can't be built | blocks | model, public_form, validator | new warning (bundle that replaces a pass) |
| 2 | FR-2 | The spec example teaches a bundle as an add-on | wrong_result | spec_example, docs | new warning (same check as FR-1) |
| 3 | FR-3 | Event defaults contradict a ticketed setup | risk | validator, admin_ui, spec_example | new warning |
| 4 | FR-4 | Saving a past opening date opens registration with no warning | risk | admin_ui, public_form | existing for specs; no for admin |
| 5 | FR-5 | No "check this event" in admin | risk | admin_ui | n/a (surfaces the validator) |
| 6 | FR-6 | Pickers list other events' sessions and ticket types | risk | admin_ui, model | no |
| 7 | FR-7 | A promo can't require a family to register together | wrong_result | model | no |
| 8 | FR-8 | Copying an event shows no preview of the shifted dates | friction | admin_ui | no |
| 9 | FR-9 | Help text omits time zone, currency, and what "Required" means | friction | docs | no |
| 10 | FR-10 | Age bands are entered as birthdates, with no ages readout | friction | admin_ui, validator | new warning (gaps, overlaps) |
| 11 | FR-11 | A leftover inactive ticket type is copied silently | friction | validator, admin_ui | new warning |
| 12 | FR-12 | The admin language flips between Swedish and English | friction | admin_ui | no |
| 13 | FR-13 | Extra choices get one inline row at a time | friction | admin_ui | no |
| 14 | FR-14 | The event picker is empty until you type | friction | admin_ui | no |
| 15 | FR-15 | The confirmation page shows no itemised total | friction | public_form | no |
| 16 | FR-16 | Hidden `_old` copies of the dual-list widgets | cosmetic | admin_ui | no |

Summary by layer:
- **Validator could warn today:** FR-1, FR-2, FR-3, FR-10, FR-11. FR-4 is already an error for specs, but nothing checks the live admin form.
- **Model or UI change needed:** FR-1 (the fix itself), FR-4, FR-5, FR-6, FR-7, FR-8, FR-10 (the readout), FR-12 to FR-16.
- **Documentation only:** FR-2 (example and walkthrough), FR-9 (help text and its translations).

Not filed: the trial's "candidate tool list" and information needs (sections A to F of the report). They are input for the assistant's tool design, not product flaws. "Close two weeks before" and keeping the weekday on a copy are organizer judgment calls, and FR-8's preview covers the second. The admin status column wording was not verified by the trial.

---

### FR-1: An add-on for one age band can't be built

```yaml
source: trial
problem: >
  A conference sells a pass per age band and an optional paid session that only
  one age band (13-17) may buy, on top of their pass. There is no way to express
  "an add-on for holders of pass X" or "an add-on for ages A-B".
tried:
  - A session-bundle ticket type with the age window and "only together with" the
    13-17 pass. The public form lets each child hold one ticket, so the bundle is
    a replacement for the pass, and it is disabled because the child would then
    have no pass.
  - A session-scoped extra. Extras have no age window and no ticket-type gate.
workaround:
  used: A session-scoped extra for every child, with no age limit. The bundle ticket type was left inactive.
  cost: wrong_result
desired: >
  An add-on bought on top of a pass and limited to an age band or to holders of
  given ticket types: an age window or a ticket-type gate on Extra, or a bundle
  the form offers in addition to the pass. Catalog §2.4 and §3.4 discuss both;
  §3.4 deferred the ticket-type gate until a real case appeared, and this is one.
touches: [new:extra_eligibility, field:Extra.applies_to, field:TicketType.kind, spec:ticket_types[].requires_ticket_type, spec:extras[].session]
severity: blocks
reach: some_events
layers: [model, public_form, validator]
validator: new_warning   # bundle_replaces_pass (proposed): a session_bundle whose age window and applies_to overlap an active event ticket, or which requires one, can never be bought alongside it
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#deviations-from-the-brief"}
  - {kind: spec_path, ref: "ticket_types[].kind"}
  - {kind: doc, ref: "docs/roadmap/event_registration_ux_case_catalog.md#34-extras-gated-by-ticket-type"}
dedupe_key: new:extra_eligibility#age-window
status: confirmed
```

### FR-2: The spec example teaches a bundle as an add-on

```yaml
source: trial
problem: >
  The worked example served to LLMs (GET /api/event-specs/schema/) models "a
  Saturday workshop for ages 13-17" as a session_bundle ticket type with the same
  age window as the 13-17 pass. On the public form that is a choice between the
  pass and the workshop, not the add-on the example's name implies. A model will
  copy the pattern.
tried: []
workaround: null
desired: >
  Change example.json to something the form actually does: a session-scoped extra
  (with a note that it is not age-limited, until FR-1), or a bundle that is
  explicitly an alternative to the pass. Add a capabilities note that a person
  holds one ticket, so a bundle replaces a pass. Say the same in
  registration-setup-walkthrough.md.
touches: [spec:ticket_types[].kind, field:TicketType.kind]
severity: wrong_result
reach: most_events   # every assistant-authored spec reads the example
layers: [spec_example, docs]
validator: new_warning   # the FR-1 warning would fire on the example itself; a test that the example validates with no warnings keeps it honest
evidence:
  - {kind: doc, ref: "backend/events/event_spec/example.json"}
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#stuck-point-table"}
dedupe_key: spec:ticket_types[].kind#example
duplicate_of: null   # related to FR-1, fixed separately and sooner
status: confirmed
```

### FR-3: Event defaults contradict a ticketed setup

```yaml
source: trial
problem: >
  A new event defaults to door rule "open: no ticket required". For a ticketed
  conference this means anyone checks in without a pass, and the events list
  shows it plainly. The event's flat price field reads "leave blank for a free
  event", but once the event has active ticket types the field is ignored. If
  every ticket type is later deactivated, the flat price silently applies again.
tried: []
workaround:
  used: Left both alone. The door rule stayed "open" in both runs.
  cost: wrong_result
desired: >
  Warn when the door rule is open but the event has priced ticket types, and when
  a flat price is set alongside active ticket types. Consider the default door rule
  following the first ticket type that is added. Help text on the price should say
  it applies only to events without ticket types. example.json also sets "open".
touches: [field:Event.ticket_rule_default, field:Event.price, cap:event_settings]
severity: risk
reach: most_events
layers: [validator, admin_ui, spec_example]
validator: new_warning   # ticket_rule_open_with_tickets, event_price_ignored (proposed)
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#labels-help-text-and-errors-that-misled"}
  - {kind: spec_path, ref: "event.ticket_rule_default"}
  - {kind: doc, ref: "backend/registrations/pricing.py calculate_total"}
dedupe_key: field:Event.ticket_rule_default#ticketed
status: confirmed
```

### FR-4: Saving a past opening date opens registration with no warning

```yaml
source: trial
problem: >
  An organizer who wants to see the public form before launch has no preview. A
  future opening date shows "registration has not opened". Moving it into the past
  makes the draft public the moment it is saved, with no confirmation. The spec
  path refuses an open window ("a person opens registration, not the spec"), but
  the admin form allows it silently.
tried:
  - Set an opening date in the future, then could not check the form.
  - Moved the opening date into the past, which opened registration.
workaround:
  used: Opened registration on a test event to check the form.
  cost: wrong_result
desired: >
  A confirm step when a save would open registration ("this makes the form
  public now"). Separately, a preview of the public form for a not-yet-open event,
  as in registration_form_builder.md "Preview".
touches: [code:registration_open, code:registration_open_on_target, field:Event.registration_opens_at]
severity: risk
reach: most_events
layers: [admin_ui, public_form]
validator: existing   # for specs only; the admin form has no equivalent
evidence:
  - {kind: validation_code, ref: registration_open}
  - {kind: trial, ref: "2026-11-19-run1-validate.txt"}
dedupe_key: code:registration_open#admin-save
status: confirmed
```

### FR-5: No "check this event" in admin

```yaml
source: trial
problem: >
  The only way to learn that something is wrong with a setup (an open window, an
  unbuyable ticket type) is the event_spec validate command or its API. An
  organizer in admin sees nothing.
tried:
  - Looked for a check in admin; ran the CLI instead.
workaround:
  used: The CLI, which an organizer does not have.
  cost: not_possible
desired: >
  An admin action or event-page panel that exports the event and shows validate's
  errors and warnings with links to the rows. It is option C in
  registration_form_builder.md, and it is where FR-1, FR-3, FR-10 and FR-11 would
  surface.
touches: [admin:event_check, cap:event_settings]
severity: risk
reach: most_events
layers: [admin_ui]
validator: existing   # the checks exist; the surface does not
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#stuck-point-table"}
  - {kind: doc, ref: "docs/roadmap/staff_ui_plan.md"}
dedupe_key: admin:event_check
status: confirmed
```

### FR-6: Pickers list other events' sessions and ticket types

```yaml
source: trial
problem: >
  On a ticket type, the sessions list shows every event's sessions, and "can only
  be bought together with" lists every event's ticket types. With several events
  in one database, including demo data, it is easy to pick a row from the wrong
  event.
tried:
  - Used the dual-list filter box to find the right session.
workaround:
  used: Filtered by name and checked carefully.
  cost: extra_steps
desired: >
  Limit both pickers to the ticket type's event, and refuse a cross-event reference
  in the model's clean() as the spec already does.
touches: [field:TicketType.sessions, field:TicketType.requires_ticket_type]
severity: risk
reach: most_events
layers: [admin_ui, model]
validator: no   # spec references are per event, so the spec can't express the mistake
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#labels-help-text-and-errors-that-misled"}
dedupe_key: field:TicketType.sessions#cross-event
status: confirmed
```

### FR-7: A promo can't require a family to register together

```yaml
source: trial
problem: >
  The brief has a discount code "for families registering together": it should
  apply only when a registration includes at least one adult and one child. A
  promo can be limited to ticket types, but not to the makeup of the registration.
  The use limit counts total uses, not per family.
tried:
  - Looked for a condition field on the promo code; set the code to apply to adult tickets only.
workaround:
  used: A plain percent code on adult tickets, usable by an adult registering alone.
  cost: wrong_result
desired: >
  A promo condition on the registration's makeup (minimum adults and children),
  next to the existing ticket-type scope. Related to sibling discounts and family
  groups, which are listed as unsupported.
touches: [new:promo_conditions, cap:family_groups, cap:sibling_discount, field:PromoCode.applies_to_ticket_types]
severity: wrong_result
reach: some_events
layers: [model]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#deviations-from-the-brief"}
  - {kind: doc, ref: "docs/roadmap/event_registration_ux_case_catalog.md#54-promo-codes-stacking-scoping-and-hidden-ticket-types"}
dedupe_key: new:promo_conditions#family-makeup
status: confirmed
```

### FR-8: Copying an event shows no preview of the shifted dates

```yaml
source: trial
problem: >
  The copy form asks for a new start date and says every date shifts by the same
  number of days. It does not show the resulting session times, sale window, age
  bounds, or whether the copy's registration would already be open. Picking "the
  same weekday next year" is left to the organizer.
tried:
  - Chose a start date by hand to keep a Saturday session on a Saturday.
workaround:
  used: Copied, then read the result.
  cost: extra_steps
desired: >
  A preview step listing every shifted date and the copy's registration status,
  with a hint when the new start falls on a different weekday. The spec diff can
  produce it.
touches: [admin:copy_event]
severity: friction
reach: most_events   # recurring events are the main case (option A)
layers: [admin_ui]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#run-2-test-conference-2028-from-a-copy"}
dedupe_key: admin:copy_event#preview
status: confirmed
```

### FR-9: Help text omits time zone, currency, and what "Required" means

```yaml
source: trial
problem: >
  Date-time fields don't say which time zone they are in. Currency is only
  mentioned on the event's flat price, not on ticket types or extras. On an extra,
  "Required" reads as "must choose one, like accommodation"; it does not say that
  it applies to every attendee with a ticket, that guardian-only parents skip it,
  or that a size list also needs "Requires choice". "Hidden" and "Active" on ticket
  types are not explained against each other.
tried:
  - Inferred the time zone from export offsets; ticked both Required and Requires choice by trial.
workaround:
  used: Guessed, then checked on the public form.
  cost: extra_steps
desired: >
  Help text: "Times are in <instance time zone>", "Price in SEK" on every price,
  "Required for every attendee with a ticket" on Extra.required, and one line on
  when to use Hidden versus Active. Both catalogues updated.
touches: [field:Event.registration_opens_at, field:TicketType.price, field:Extra.required, field:Extra.requires_choice, field:TicketType.is_hidden]
severity: friction
reach: most_events
layers: [docs]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#things-i-was-not-sure-were-right"}
dedupe_key: field:Extra.required#help-text
status: confirmed
```

### FR-10: Age bands are entered as birthdates, with no ages readout

```yaml
source: trial
problem: >
  Age bands are set as birthdate bounds judged on the event's start date, so the
  organizer converts "ages 13-17" into two dates by hand. Nothing shows which ages
  a set of bounds covers, or that two bands leave a gap or overlap.
tried:
  - Computed the bounds by hand and confirmed them on the public form.
workaround:
  used: Manual date arithmetic.
  cost: extra_steps
desired: >
  Enter ages, or show a live readout ("ages 13-17 at event start"). A warning for
  age gaps and overlaps between active child ticket types. On a copy the bounds
  shift with the dates, which is correct, and the readout would show it.
touches: [field:TicketType.min_birthdate, field:TicketType.max_birthdate, cap:ticket_types]
severity: friction
reach: most_events
layers: [admin_ui, validator]
validator: new_warning   # age_band_gap, age_band_overlap (proposed)
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#stuck-point-table"}
dedupe_key: field:TicketType.min_birthdate#ages
status: confirmed
```

### FR-11: A leftover inactive ticket type is copied silently

```yaml
source: trial
problem: >
  An inactive ticket type left over from a failed attempt is copied into next
  year's event, still inactive, with no notice. It also keeps its "only together
  with" dependency.
tried: []
workaround:
  used: None; the row sits in both events.
  cost: none
desired: >
  A warning for inactive rows that nothing refers to, and a copy option to leave
  inactive rows out (or a list of them on the copy preview, FR-8).
touches: [admin:copy_event, field:TicketType.is_active]
severity: friction
reach: some_events
layers: [validator, admin_ui]
validator: new_warning   # inactive_unreferenced (proposed)
evidence:
  - {kind: trial, ref: "2026-11-19-run2-export.json"}
dedupe_key: field:TicketType.is_active#copy
status: confirmed
```

### FR-12: The admin language flips between Swedish and English

```yaml
source: trial
problem: >
  The admin rendered in English, then in Swedish, with no change by the user.
  Likely cause: the admin follows the language cookie that the public site's
  switcher sets (staff_ui_plan.md, "D. Fix the bilingual mess"), so visiting the
  public form changes the admin language.
tried: []
workaround:
  used: None.
  cost: none
desired: >
  The admin language follows the staff user's own setting, not the public site's
  cookie, or switching visibly says it affects both.
touches: [admin:language]
severity: friction
reach: most_events
layers: [admin_ui]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#method-and-honesty-notes"}
  - {kind: doc, ref: "docs/roadmap/staff_ui_plan.md"}
dedupe_key: admin:language
status: confirmed
```

### FR-13: Extra choices get one inline row at a time

```yaml
source: trial
problem: >
  A new extra shows one empty choice row. A four-size list needs three clicks on
  "add another" first.
tried: []
workaround:
  used: Clicked "add another" per choice.
  cost: extra_steps
desired: Show several empty choice rows on a new extra.
touches: [field:ExtraChoice.label]
severity: friction
reach: most_events
layers: [admin_ui]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#things-i-did-twice"}
dedupe_key: field:ExtraChoice.label#inline-rows
status: confirmed
```

### FR-14: The event picker is empty until you type

```yaml
source: trial
problem: >
  The event field on a ticket type is a search dropdown that shows nothing until
  you type. A new organizer may think no events exist.
tried: []
workaround:
  used: Typed part of the event name.
  cost: extra_steps
desired: Show recent or upcoming events when the field gets focus, or prefill it when adding from an event's page.
touches: [field:TicketType.event]
severity: friction
reach: most_events
layers: [admin_ui]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#stuck-point-table"}
dedupe_key: field:TicketType.event#picker
status: confirmed
```

### FR-15: The confirmation page shows no itemised total

```yaml
source: trial
problem: >
  After submitting, the guardian sees a summary but no price per line, so they
  can't check the stored total against the running total they saw.
tried: []
workaround:
  used: None.
  cost: none
desired: Line-by-line prices, the discount, and the total on the confirmation page and in the email.
touches: [cap:line_items]
severity: friction
reach: most_events
layers: [public_form]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#final-check-on-the-frontend"}
dedupe_key: cap:line_items#confirmation
status: confirmed
```

### FR-16: Hidden `_old` copies of the dual-list widgets

```yaml
source: trial
problem: >
  The ticket type and promo forms contain hidden `sessions_old` and
  `applies_to_ticket_types_old` selects behind the dual-list widgets. Invisible to
  a person, but an agent or screen reader reading the form sees duplicate fields.
tried: []
workaround:
  used: Ignored them.
  cost: none
desired: Remove the duplicates, or mark them hidden from assistive technology.
touches: [field:TicketType.sessions, field:PromoCode.applies_to_ticket_types]
severity: cosmetic
reach: most_events
layers: [admin_ui]
validator: no
evidence:
  - {kind: trial, ref: "2026-11-19-agent-ui-trial.md#labels-help-text-and-errors-that-misled"}
dedupe_key: field:TicketType.sessions#old-widget
status: confirmed
```
