# Agent-driven UI trial: registration setup in Tryggare (2026-11-19)

An AI agent stood in for an organizer and followed `docs/registration-setup-walkthrough.md` through the Django admin and the public frontend in a real browser. Timings are agent wall-clock times, not human times: they show the number of steps and where the product forced a detour, not how long a person would take.

## Method and honesty notes

- **Browser.** Playwright on this NixOS host could not launch its bundled Chromium (missing shared libraries). I used a Nix-provided Chromium 149 (`nix shell nixpkgs#chromium`) in headless mode, driven over CDP with small Python scripts. All configuration went through browser form submits. Scripts and screenshots are in `/tmp/trial/`, outside the repo.
- **Account.** An `organizer` user was created via `manage.py shell` with `accounts.roles.grant(u, roles.ADMINISTRATOR)`, plus `is_staff`. It is not a superuser. I read only `roles.py`.
- **Non-UI reads.** `event_spec export` and `event_spec validate` for the two snapshots; `podman logs` for demo-reset lines; one `env | grep EMAIL` in the web container to check that no real mail could leave.
- **Not read.** Source code, tests, `event_spec/`, the plan docs, and the API.
- **Docs actually read.** The walkthrough, and `specification.md` "Data Model" (lines 8-80). The Data Model section is about check-in rules and tickets for attendees. It says nothing about ticket types, extras, promo codes or prices, so it did not help build a form.
- **Demo reset.** The last reset logged was 15:19, so none hit during the run (about 15:56 to 16:04). The next one was due about 16:19.
- **Invented data.** "Testfamilj", `test.family@example.invalid`, phone 0700000000. No health information was entered.
- **Admin language.** The admin started in English and later rendered in Swedish. I did not change it. The language switch is a cookie or profile setting, and the Swedish page headings behaved the same. A real organizer could be surprised by this.

## Run 1: "Test Conference 2027" from scratch

Event id `9de12a6b-be0e-4fca-a502-11319b02c4e7`.

| Total | Time to first working ticket | Registration page matched the brief? |
|---|---|---|
| about 6.5 min (15:55:59 to 16:02:31) | about 1 min (adult ticket saved at 15:57:13) | Partly (see deviations) |

### What was built

| Brief item | Built as |
|---|---|
| Event, three days | 2027-06-04 to 2027-06-06 (Fri to Sun). Opens 2026-11-01 09:00 (changed, see stuck points). Closes 2027-05-21 23:59, two weeks before the start. |
| Adult pass 1200 SEK, parents | Ticket type "Adult conference pass": applies_to Parent, price 1200, capacity 150. |
| Child pass 0-12, 300 | applies_to Child, min_birthdate 2014-06-05, max blank. |
| Child pass 13-17, 600 | applies_to Child, min_birthdate 2009-06-05, max_birthdate 2014-06-04. |
| Saturday workshop add-on, 150, children 13-17 | Not buildable as written. See deviations. Built as a Session ("Saturday workshop", 2027-06-05 10:00-12:00, rule "children") plus an Extra scoped to that session, applies_to Child, 150 SEK. There is no age restriction. |
| T-shirt 200 SEK, one per person, S/M/L/XL, required with a ticket | Extra: per attendee, applies_to Either, requires_choice and required ticked, four choices. |
| Promo TESTFAMILY, 10%, adult tickets only | Percent, 10, applies_to_ticket_types = Adult pass. "For families registering together" has no field. |
| Capacity: adult 150, child unlimited | Capacity 150 on the adult pass, blank on the child passes. |

### Final check on the frontend

The page is `http://localhost:5173/register/<event-id>/`. I registered one invented family: one parent with the adult pass and a t-shirt (M), and one child born 2013-03-10 with the 13-17 pass, a t-shirt (S) and the workshop.

- **Prices.** The running total was correct. 1200 + 600 + 200 + 200 + 150 = 2350. With TESTFAMILY, the discount was -120 (10% of the adult pass only) and the total 2230. A summary price per line was not shown after submit, so I could not confirm the stored total.
- **Ticket choices follow age.** The child's ticket dropdown disables ineligible types by birthdate. Born 2020 gets 0-12 only; born 2013 gets 13-17; born 2005 gets nothing. Each disabled option is annotated "(13-17 år)" or "(upp till 12 år)".
- **T-shirt.** Offered to the parent and the child. For a "guardian only, no ticket" parent it is correctly hidden, with the explanatory text "deltar inte själv - därför ställer vi inga hälsofrågor eller tillval".
- **Workshop.** Offered under "Tillval" to the child. It is not age-restricted: a 5-year-old would also be offered it (not tested live; the brief's age rule is simply not representable).
- **Promo.** It applied only to the adult ticket, as configured.
- **Submit.** It reached "Bekräfta din e-post" with reference `AWD35YRY` and a summary. I did not click any confirmation link. The mail host is empty in this container, so nothing could be sent.
- **Language.** The public page is Swedish only.

### Snapshots

- `docs/trials/2026-11-19-run1-export.json`.
- `docs/trials/2026-11-19-run1-validate.txt`. Validation **failed with 2 errors, 0 warnings**: `registration_open_on_target` and `registration_open`. Both are because I had moved `registration_opens_at` into the past to make the final check possible. They are not about the content.
- The export was taken before the final-check registration was submitted.

## Run 2: "Test Conference 2028" from a copy

Event id `c0890638-64eb-4923-b042-effa858b489e`.

| Total | Time to first working ticket | Registration page matched? |
|---|---|---|
| about 1 min of edits (16:02:36 to 16:03:12), plus about 2 min of discovery the copy form and finding the list | n/a: the copy already contained tickets | Not tested in the frontend: the copy's registration is "not open yet" (opens 2027-10-31). Verified through the export instead. |

- **Copy action.** Events list, tick the row, choose "Kopiera evenemang..." (Copy event...). A small form asks for the new name and a new start date. All dates and times shift by the same number of days.
- **Start date.** I chose 2028-06-02, a Friday, so the Saturday workshop stays on a Saturday (2028-06-03). Exactly one year later would be 2028-06-04, a Sunday. This is a judgment call I had to make.
- **What the copy shifted.** Event 2028-06-02 to 06-04; registration opens 2027-10-31, closes 2028-05-19 (still 14 days before). The age windows were shifted too: 0-12 min 2015-06-03; 13-17 min 2010-06-03, max 2015-06-02. The copy does not copy registrations. Capacity, promo, extras and choices were copied.
- **Changes applied.** Adult 1320, child 0-12 330, child 13-17 660, workshop ticket type 165 (the unused bundle) and workshop extra 165, t-shirt 220. The t-shirt choice price_delta is 0, so there is nothing to round. Promo code renamed to `TESTFAMILY28`. XXL added as a fifth t-shirt choice.
- **Verification.** `event_spec validate` returned valid with no errors and no warnings.
- **Snapshots.** `docs/trials/2026-11-19-run2-export.json`, `docs/trials/2026-11-19-run2-validate.txt`.

## Stuck-point table

| Time | What I was trying to do | Where I looked | What I tried | What happened | Would have helped |
|---|---|---|---|---|---|
| 15:55 | Get a working browser | Host | Playwright's Chromium, then Nix Chromium | Bundled browser failed on missing libs; Nix Chromium worked | (Tooling, not product) |
| 15:56 | Know what age bounds mean | Ticket type help text | Computed from "counted on the event's start date" | Fine, but I had to do the date maths myself (age 13-17 on 2027-06-04 means born 2009-06-05 to 2014-06-04). Frontend confirmed it. | Age-in-years fields, or a live "ages covered at event start: 13-17" readout |
| 15:56 | Pick the Event on a ticket type | Event field | Typed into the select | It is a search dropdown, empty until you type; a person might think no events exist | Show a short list on focus |
| 15:57 | Link the workshop add-on to ticket types | Ticket type, Session ticket forms | Used a "Session bundle" ticket type with a "can only be bought together with" rule | The public form lets a child pick one ticket only, so the bundle shows as disabled: "kräver Child pass 13-17" | Doc saying a session bundle is a separate ticket, not an add-on |
| 15:58 | Model an add-on limited to age 13-17 | Extra form | Session-scoped Extra | No age/birthdate fields exist on Extra; the age limit cannot be enforced | Birthdate window or "requires ticket type" on Extra |
| 15:58 | See the public page | Events list "Anmälningsperiodens status" | Opened the page | "Anmälan har inte öppnat än": I chose an opening date in the future (2027-01-15) and that blocked the final check. I moved opening to 2026-11-01. | A warning on save: "registration is not open yet, so the page will show a closed message" |
| 15:59 | Tell whether anything is wrong | Admin | `event_spec validate` | Admin has no "check this event" button; only the CLI told me registration was already open | A "validate event" admin action or checklist |
| 16:00 | Pick the right widget for sessions | Ticket type form | Filter box on a dual-list | The Sessions list shows sessions of all events, including seeded 2026 events; easy to pick the wrong one | Filter the list by the chosen event |
| 16:02 | Check "required if buying a ticket" for t-shirt | Extra form, "Required" | Ticked Required + Requires choice | Works on the page, but the help text ("Must-choose-one, e.g. accommodation") does not say that Required applies per attendee ticket, nor that guardian-only parents skip it | Clearer help: "Required for every attendee with a ticket" |
| 16:02 | Pick a start date for the copy | Copy event form | Chose a Friday | The form only says dates shift by the same number of days; it does not show the resulting open/close dates or whether the copied registration would already be open | Preview of shifted dates before confirming |

## Deviations from the brief

- **Saturday workshop, 13-17 only, as an add-on: not buildable as written.**
  - Tried as a Session-bundle ticket type with the age window and "can only be bought together with: Child pass 13-17". The public form treats it as a *replacement* for the child's ticket, and disables it because the child would then have no 13-17 pass.
  - Built instead as an Extra on the Saturday session with no age limit. It is offered to every child.
  - The inactive bundle ticket type is still in the event (the copy has it too). It should be deleted by a tidier organizer.
- **Registration opens "on a date you choose".** The brief makes the open date free, but a date in the future makes the final check impossible. I set it to a past date. Because of that, `validate` rejects the event spec (`registration_open_on_target`, and the opens-at must be "a future moment").
- **Promo "for families registering together".** No field expresses this. I left it as a plain percent code for adult tickets. `Max Uses` would limit total use, not "per family".

## Labels, help text and errors that misled

- **"Hidden" and "Active" on ticket types.** Both exist; "Active" is ticked by default. If you copy an event whose bundle ticket is inactive, the copy shows it as inactive too. Nothing tells you that.
- **"Required" on Extra.** Help says "must-choose-one, e.g. accommodation - renders as radio". "Requires choice" is a separate tick. Both had to be ticked for a t-shirt size.
- **"Default Ticket Rule: open" on the event.** The events list shows "Open - no ticket required" for a ticketed conference. At the door this means anybody checks in without a pass. The brief never said anything about door rules, but the default looks like a mistake.
- **Event "Price" field.** Leaving it blank is right, but a conference organizer might fill it in and double-charge.
- **Swedish "Anmälan har inte öppnat än" for open page.** The admin list says "Öppen/Inte inställd" in the status column; for my event it said "Öppen" in the admin even before I moved the date. I did not capture the pre-fix status text reliably, so treat that as unverified.
- **Admin language flip.** English at first and Swedish later, with no action from me.
- **The Sessions widget** lists all events' sessions; **the "Can only be bought together with" select** lists all events' ticket types.
- **Doubled form widgets.** The raw dump of the page shows `sessions_old` / `applies_to_ticket_types_old` selects behind the dual-list widget. Cosmetic, but an agent reading the form sees duplicate fields.

## Things I did twice

- The Event "opens at" date (set it, then moved it).
- The workshop (ticket type bundle, then Extra).
- Inline choice rows: the Extra form shows only one empty row; I had to click "Add another Extra Choice" three times.

## Things I was not sure were right

- Whether age bounds are inclusive. The help text says "born on or after" and "born on or before", counted on the event's start date. The frontend confirmed the behaviour for a 14-year-old.
- Whether "closes two weeks before the event" means the last day or the day before. I used 2027-05-21 23:59, exactly 14 days before 06-04.
- The time zone. Dates in the export are `+01:00` / `+02:00` Europe/Stockholm. Nothing in the admin says which time zone the form fields are in.
- Currency: SEK only, stated in the Price help text, but there is no currency on ticket types or extras.
- Whether the promo code applied to child tickets: it did not, as expected (confirmed in the frontend).

## Information needs (grouped)

Each line: what I needed, where I found it, confidence, and the tool call I would want without a UI.

### A. Does it exist already?
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Is there already an event with this name or dates? | Events list | High | `list_events(name?, date_range?)` returning id, dates, registration status |
| What ticket types, extras, sessions, promo codes does an event have? | Separate admin lists, filtered with `?q=` | Medium (several pages) | `get_event_setup(event_id)`: one structured snapshot |
| Which seeded events share the database (so I do not pick their sessions)? | Noticed in the Sessions widget | Medium | `list_events`, with a flag for demo data |
| What is the current registration status of an event (not open / open / closed)? | Events list column; public page | High | `get_registration_status(event_id)` with the open and close times and the reason |

### B. Field meaning and allowed values
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Allowed values of Applies To, Kind, Discount Type, Ticket Rule | Dropdown options | High | `describe_schema(entity)` listing fields, types, enum values, defaults, required-ness |
| What Required / Requires choice / Per attendee mean together | Help text, then trial on the frontend | Medium | `explain_field(entity, field)` with an example |
| Which fields are required on each form | Trial and error (save errors) | Medium | `describe_schema` including required flags |
| Defaults that are risky (Default Ticket Rule = open; Hidden/Active) | Seen on the form | Medium | A "review defaults" report |

### C. Dates, ages, money and time
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| How age bounds work (inclusive, counted on which date) | Ticket type help text; confirmed on the frontend | Medium-high | `age_window_to_birthdates(event_id, min_age, max_age)` returning min/max birthdates; reverse: `describe_ticket_age_window(ticket_id)` |
| Which time zone the date/time fields are in | Not found; inferred from export offsets | Low | Field-level `timezone` in `describe_schema` |
| Currency | Event Price help text (SEK only) | High | Same |
| Whether the close date is two weeks before the start, in the event's own time zone | Computed by hand | Medium | `compute_dates(event_start, offset_days)` |
| What shifted dates a copy will give | Only visible after copy | Low | `preview_copy(event_id, new_start_date)` showing every shifted date |

### D. Relationships
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Which ticket does a session or extra attach to | Not documented; tried bundle ticket vs. session extra | Low | `explain_modelling(use_case="add-on for a session limited to an age band")` and a per-ticket list of sessions and extras that apply |
| Can a person buy two tickets (a pass and a bundle)? | Discovered on the public form (disabled option) | Low | `preview_form(event_id, attendee_profile)` returning offered and disabled options with reasons |
| Do sessions belong to an event, and to which one | Event field on the session form | High | `list_sessions(event_id)` |
| Which promo applies to which tickets | Multi-select on the promo form | High | `get_promo(event_id, code)` with the ticket types it affects |

### E. Verifying the result
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Is the setup consistent (no overlapping age bands, gaps, open registration)? | `event_spec validate` (CLI only) | Medium | `validate_event(event_id)`: errors, warnings, and age-band coverage (ages with no ticket, overlaps) |
| What does the public page show? | Frontend in a browser | High | `preview_form(event_id)`: tickets, extras, labels as a family would see them |
| What would a given family pay? | Typing a family into the public form | High | `preview_price(event_id, family: [{role, age, ticket, extras, size}], promo_code?)` returning a line-by-line total |
| Did the registration go through, what is stored? | Summary page after submit | Medium | `get_registration(reference)` with its lines and total |
| What did the setup look like before and after an edit? | Export only | Medium | `diff_events(a, b)` or `export_event(event_id)` |

### F. Copying
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| What the copy action copies and what it leaves out | Copy form text (registrations, tickets and check-ins not copied) | High | `preview_copy` |
| How to change every price by a percentage and round | By hand (5 edits) | Medium | `bulk_update_prices(event_id, factor, rounding)` |
| Rename a code (TESTFAMILY to TESTFAMILY28) | Edit the promo | High | `update_promo(...)` |
| Add one choice to an existing extra | Inline row on the Extra | Medium | `add_extra_choice(extra_id, label, price_delta?)` |

## Candidate tool list for a future agent

1. `list_events`, `get_event_setup`, `get_registration_status`: read what exists.
2. `describe_schema(entity)` and `explain_field(entity, field)`: field meaning, enums, required-ness, defaults, units (SEK, time zone).
3. `age_window_to_birthdates(event_id, min_age, max_age)` and its inverse.
4. `create_event`, `create_ticket_type`, `create_session`, `create_extra` (with choices), `create_promo_code`, and matching `update_*`; sessions and ticket types addressed by name inside one event.
5. `explain_modelling(use_case)`: how to express "an add-on for one session, limited by age", "a free dependent ticket", "per-family discount".
6. `preview_form(event_id, attendee_profile)`: what the public form offers and disables, with the reasons.
7. `preview_price(event_id, family, promo_code?)`: itemised total with discount.
8. `validate_event(event_id)`: consistency, age-band gaps and overlaps, registration dates, risky defaults, orphan inactive items.
9. `preview_copy(event_id, new_start_date)` and `copy_event(...)`, returning every shifted date.
10. `bulk_update_prices(event_id, factor, rounding)`.
11. `export_event` and `diff_events`.
12. A guard on opening registration (a confirm step), since opening it early blocks `validate` and exposes a draft.

## Counts

- Browser scripts run: about 45, one per UI step or probe (a form dump, a fill-and-submit, or a page read).
- Screenshots: 36 PNGs saved to `/tmp/trial/`. I viewed one (the ticket type add form); the rest were captured for the record, and I mostly read page text instead.
- Saved forms: about 20 (1 event, 4 ticket types, 1 session, 2 extras, 1 promo, 1 event edit, then run 2: 1 copy, 5 price edits, 1 promo edit, 1 extra edit).
- Documentation read: 2 files.
- Asked a human or an AI for help: no.
