> **Stale server:** this run hit a web container started before the `feat/setup-checker` commits, so Check setup and extra gating were absent. See `2026-11-19-agent-ui-trial-run3.md` for the valid run.

# Agent-driven UI trial, second run: registration setup in Tryggare (2026-11-19)

An AI agent again stood in for an organizer and followed `docs/registration-setup-walkthrough.md` through the Django admin and the public frontend in a real browser. Timings are agent wall-clock times, not human times. First run's report: `docs/trials/2026-11-19-agent-ui-trial.md`.

## Headline finding: the new features were not in the running admin

The dev stack's `tryggare_web_1` has run `daphne` with no autoreload for 9+ hours (`podman top`: elapsed 9h6m at 19:25), but the branch (`feat/setup-checker`) has commits from 18:38 to 19:07. The admin I was served therefore did not contain the changes this run was meant to test:

- **No "Check setup" action.** The Events list offers exactly three actions: Delete selected, Generate / refresh report snapshot, Copy event. No other events admin list (ticket types, extras, sessions) has one, and neither does the event change page (checked all links and buttons). I could not run it in either run.
- **No "requires ticket types" field on Extras.** The Extra add form (with an event picked, so any event-dependent field would have appeared) has Event, Session, Name, Price, Per Attendee, Applies To, Requires Choice, Required, Default Selected, Sort Order, Active, choices. Nothing ties an extra to ticket types.

I was told not to restart containers and not to read source, so I could not confirm the cause, and I do not know whether a restart would show both features. What I can say is that an organizer on this stack sees neither. Everything under "Compared with the first run" that depends on those two features is therefore **unchanged, by absence**, not a verdict on the code. A re-run after `date > restart-dev.txt` (or a container restart) would settle it.

## Method and honesty notes

- **Browser.** Nix Chromium 149 (`nix shell nixpkgs#chromium`), headless, driven over CDP with `uv run --with playwright python`. Scripts and screenshots are in `/tmp/trial2/`, outside the repo.
- **Account.** `organizer2`, created with `manage.py shell` and `accounts.roles.grant(u, roles.ADMINISTRATOR)`, `is_staff` true, not superuser. I read only `roles.py` and the project `CLAUDE.md` (for the dev stack, not credentials). All configuration was form submits in the browser.
- **Non-UI reads.** Two `event_spec export` calls, `podman top` / `podman inspect` / `git log` (metadata only, to explain the missing features), and the account creation shell.
- **Not read.** Source, tests, `event_spec/`, plan docs, the feature-requests doc, the API.
- **Docs read.** The walkthrough only. I did not re-read the data-model doc (the first run found it did not help).
- **Demo reset.** Reset is due at :19; I waited until 19:24 to start and finished at 19:28:34. The data persisted through both runs, so none hit. `podman logs tryggare_web_1` was empty when I checked afterwards, so the reset lines could not be confirmed that way.
- **Side effect to know about.** `podman exec ... uv run python manage.py shell` printed "Uninstalled 12 packages" (e.g. `django-stubs`) in the web container's venv. The web process was unaffected, but it is a surprise for a read-only-looking command.
- **Invented data.** "Testfamilj", `test.family@example.invalid`, phone 0700000000, children "Kid" and "Minior". No health data.
- **Language.** The admin was English until the copy form, then Swedish from then on, with no action from me.

## Run 1: "Test Conference 2027" from scratch

Event id `0b18ee80-20d0-49fa-b13f-9ac2f2987b4f`.

| Total | Time to first working ticket | Registration page matched the brief? |
|---|---|---|
| about 3.2 min (19:24:17 login to 19:27:30 submitted family); setup alone about 2.5 min (19:24:21 to 19:26:52) | about 1 min (adult pass saved about 19:25:24) | Partly (workshop not age-limited) |

### What was built

| Brief item | Built as |
|---|---|
| Event, three days | 2027-06-04 to 06-06. Opens 2027-01-15 09:00 first (so the page said "Not open yet"), then changed to 2026-11-01 09:00. Closes 2027-05-21 23:59. |
| Adult pass 1200, parents | Applies To Parent, capacity 150. |
| Child 0-12, 300 | Child, min birthdate 2014-06-05. |
| Child 13-17, 600 | Child, min 2009-06-05, max 2014-06-04. |
| Saturday workshop, 150, children 13-17 only | Session (2027-06-05 10:00-12:00) plus an Extra on that session, Applies To Child, 150. **No age limit possible**, see deviations. |
| T-shirt 200, per person, S/M/L/XL, required | Extra: per attendee, Either, Requires Choice and Required ticked, four choices. |
| Promo TESTFAMILY, 10%, adult only | Percent 10, applies to the adult ticket type. |
| Capacity | 150 on the adult pass, blank on child passes. |

### Final check on the frontend

Page `http://localhost:5173/register/0b18ee80-.../`. One parent (adult pass, T-shirt M), child "Kid" born 2013-03-10 (14 at the event: 13-17 pass, T-shirt S, workshop), child "Minior" born 2018-05-01 (0-12 pass, T-shirt L, no workshop ticked).

- **Prices.** Subtotal 1200 + 200 + 600 + 200 + 150 + 300 + 200 = 2850. TESTFAMILY gave -120 (10% of the adult pass only), total 2730. The confirmation page showed the same total, lines per person, and "Rabatt (TESTFAMILY) -120,00 kr". Matches the setup.
- **Ticket choices follow age.** For the 14-year-old the 0-12 option is disabled and annotated "(upp till 12 år)". For the 9-year-old the 13-17 option is disabled, annotated "(13-17 år)".
- **Saturday workshop: offered to every child.** It showed under "Tillval" for the 9-year-old exactly as for the 14-year-old, and even before a birthdate was entered. **The brief's rule (13-17 only) was not met.**
- **T-shirt.** Offered to the parent and to both children, marked required with "*" in all three places, including while the parent's ticket is still unselected.
- **Promo.** Applied to the adult line only. The success text says "10 % rabatt på summan" ("10% off the total"), which reads as if it took 10% off the whole order; the actual discount was 10% of the adult line.
- **Submit.** Reached "Bekräfta din e-post", reference `H2XUS93Q`. I did not click any link. No email can leave this stack.
- **"Check setup".** Not run in this run, because it is not in the admin (see headline).

### Snapshot

`docs/trials/2026-11-19-rerun-run1-export.json`, taken before the final-check registration. I did not run `validate` (the brief only allows `export`).

## Run 2: "Test Conference 2028" from a copy

Event id `7c4ed01d-5e55-4d4c-b5c0-2ebab711d755`.

| Total | Time to first working ticket | Registration page matched? |
|---|---|---|
| about 21 s (19:28:13 to 19:28:34) for copy plus 7 edits | n/a, tickets came with the copy | Not tested in the frontend: opens 2027-11-02. Checked through the export. |

- **Copy.** Events list, tick the row, "Kopiera evenemang..." (Go), type a name and a start date. I chose 2028-06-04, exactly one year later, as asked.
- **What the copy produced.** Event 2028-06-04 to 06-06, opens 2027-11-02 09:00, closes 2028-05-21 23:59 (still 14 days before). Ticket age windows were recomputed on the new start date, not just shifted: 0-12 min 2015-06-05; 13-17 min 2010-06-05 and max 2015-06-04. Capacity 150, extras, choices, promo code copied. The workshop session moved to 2028-06-05, a **Monday** (a year later is a Sunday start, so the Saturday workshop is no longer on a Saturday and nothing says so).
- **Edits applied.** Adult 1320, child 0-12 330, child 13-17 660, workshop extra 165, T-shirt 220 (all +10%, no rounding needed; choice price deltas are 0, so nothing to round). Promo renamed `TESTFAMILY28`, XXL added as a fifth T-shirt choice (sort 4). No ticket-type bundle exists this time, so five price edits, not six.
- **"Check setup".** Not run (absent).
- **Snapshot.** `docs/trials/2026-11-19-rerun-run2-export.json` (export confirms every change above).

## Stuck-point table

| Time | What I was trying to do | Where I looked | What I tried | What happened | Would have helped |
|---|---|---|---|---|---|
| 19:24 | Run "Check setup" | Events list actions, event change page, other events lists | Looked in all of them, English and later Swedish | Action does not exist on the served admin; the web process predates the branch | A visible sign of which build is running; the dev stack reloading on commit |
| 19:24 | Pick the Event on a ticket type, extra, promo | Event field | Select2 autocomplete, empty until you type | Same as run 1. When I typed and picked the first result too fast it chose a **different event's** row, and the save error talked about that other event ("fall exactly on an anniversary... 2026-11-19"). | Show a short list on focus; keep the chosen event's name visible next to date errors |
| 19:25 | Know what the age bounds mean | Ticket type help | Computed birthdates by hand again | Help is accurate; the new validation message explains the anniversary rule with an example. Still hand arithmetic. | Age-in-years fields or a live "ages covered at event start" readout |
| 19:26 | Make the workshop 13-17 only | Extra form, Session form, Ticket type form | Session + session-scoped Extra, Applies To Child | No age or ticket-type field on Extra. Offered to every child (see final check). | The "requires ticket types" field the product was said to have gained |
| 19:26 | Link a promo to the adult ticket | Promo code form | Dual-list widget | The ticket type list holds every event's types (14 entries), twice (also under "Unlocks"). Easy to pick the wrong event's type. | List filtered by the chosen event |
| 19:26 | Pick the session for the workshop extra | Extra form, Session select | Typed "Saturday" | Select2 again; the empty list shows all events' sessions | Filtered by event |
| 19:27 | Open the public page after choosing a future open date | Events list status "Not open yet" | Moved opens-at to the past | Page showed a closed message until I did. The list status said "Not open yet", which is accurate but only on the list; saving the event gave no warning. | A warning on save of a future open date; "Check setup" would be the place |
| 19:28 | Pick the copy's start date | Copy form | Typed exactly one year later (a Sunday) | No preview of the resulting dates, weekdays or whether registration would be open. Workshop landed on a Monday. | Preview of shifted dates with weekdays |
| 19:28 | Add the XXL choice | Extra form, choice rows | Clicked "add another" | Only one blank row is shown (as run 1); one click was needed per extra row. Fine for one choice. | Several blank rows, or a "S, M, L" bulk entry |

## Deviations from the brief

- **Saturday workshop for 13-17 only: not buildable as written (unchanged).** Built as a session-scoped Extra for children with no age limit. The final check confirmed it is offered to a 9-year-old. The fix the product was said to ship (extras requiring ticket types) was not available in the served admin.
- **Registration opens "on a date you choose".** I chose a future date first, which blocked the page; moved to a past date to run the final check. Validation was not run this time.
- **Promo "for families registering together".** No field. Plain 10% code on adult tickets.
- **Door rule.** I left Default Ticket Rule at "Open - no ticket required" because the brief says nothing. Nothing flagged it (the checker that might have is absent).
- **Run 2 start date.** Exactly one year later is a Sunday; I took the brief literally, so the copy's workshop is on a Monday.

## Labels, help text and errors that misled

- **Promo applied message** "10 % rabatt på summan" reads as a discount on the whole order; with the promo scoped to the adult ticket it is 10% of that line only (-120 on 2850).
- **T-shirt "*" on a parent who has not picked a ticket.** Marked required before the ticket is chosen; confusing next to "Ingen biljett - enbart vårdnadshavare".
- **"Required" (Extra)** help still says "Must-choose-one, e.g. accommodation - renders as radio". It does not say that "Required" alone is not enough for a size list, or that it applies per attendee. Both "Requires Choice" and "Required" had to be ticked.
- **Age-anniversary error text** quoted the wrong event's dates when the wrong event had been picked, and gave an example year (2008-12-20) that does not relate to the event the organizer thinks they chose.
- **Admin language flip.** English at first, Swedish after the copy form, with no action from me. Unchanged.
- **Dual lists show all events' records, with doubled widgets** (`*_old` selects behind the dual list) when the page is read as a form. Unchanged.
- **Hidden / Active / Default Ticket Rule** defaults: unchanged and unflagged.
- **Copy form says dates shift "lika många dagar"** (the same number of days) but the ages were recomputed on the anniversary, which is better than the text suggests. The text understates it.

## Things I did twice

- The Event "opens at" date (future first, then past).
- The three ticket types: the first attempt saved only the adult pass; the two child passes failed on a wrong-event pick and were re-entered.

## Things I was not sure were right

- Whether the copy's dates would still be sensible: the weekday shift (Saturday workshop to Monday) was only visible in the export.
- Time zone: the form shows no zone; the export has `+01:00` and `+02:00` (the copy's close date is `+02:00`, its open `+01:00`, as expected for Stockholm summer and winter). Not stated anywhere in the admin.
- Whether 10% promo should also discount children: it did not, as configured.
- Whether the registration will actually be counted against capacity 150 (not visible).

## Compared with the first run

Marks: fixed, better, unchanged, worse. "Unchanged (absent)" means the first run's remedy depends on a feature that the served admin did not contain.

### Stuck points

| First-run stuck point | Now | Evidence |
|---|---|---|
| Know what age bounds mean; hand arithmetic | Better | The save error now explains the anniversary rule with an example date, and the copy recomputes age windows on the new start date (2015-06-05, 2010-06-05 to 2015-06-04). Entry is still by birthdate, so the arithmetic is still mine. |
| Event select is empty until you type | Unchanged | Select2 again; it also caused a wrong-event pick this run. |
| Session bundle as add-on does not work | Better | I did not try it; the workshop went straight to an Extra, so the detour was avoided, but only because I remembered the first report. Nothing in the UI says a bundle is a separate ticket. |
| Age-limited add-on impossible | Unchanged (absent) | No ticket-type field on the Extra form; workshop offered to a 9-year-old. |
| Future opens-at blocks the page; no warning on save | Unchanged | Same trap, saved with no warning. |
| No way to check the setup | Unchanged (absent) | No "Check setup" action anywhere in the admin. |
| Sessions widget lists all events' sessions | Unchanged | Same, in the extras form and the ticket type form. |
| "Required" help text on Extras | Unchanged | Same text. |
| Copy form gives no preview of shifted dates | Unchanged, partly better | Still no preview; the dates came out correct, but the weekday problem (Saturday workshop on a Monday) is not visible until later. |

### Deviations

| First-run deviation | Now | Evidence |
|---|---|---|
| Workshop 13-17 only | Unchanged (absent) | As above; final check offered it to a 9-year-old. |
| Opens-at in the past conflicts with `validate` | Not testable | I did not run validate; "Check setup" was absent. |
| Promo "for families together" | Unchanged | No field. |
| Leftover inactive bundle ticket type in the copy | Fixed (by avoidance) | There was no bundle to leave behind, since I did not build one. |

### Labels and other items

- Hidden/Active, Default Ticket Rule = Open, Event Price, admin language flip, doubled widgets, all-events lists: unchanged.
- Dual-list ticket lists in the promo form now include 14 entries across every event: unchanged.

## New things that broke or confused me

- **The running stack is stale relative to the branch** (headline). This was the biggest obstacle.
- **Select2 race.** A fast pick of the first autocomplete result selected another event's row; the save error then described the wrong event. A real organizer would see it too.
- **Workshop weekday after copying a year forward.** Silent.
- **`uv run ... manage.py shell`** uninstalled dev packages from the container venv.
- **Swedish admin after the copy action.** The language changed mid-run.

## What "Check setup" caught and missed

Not available in the served admin, so it caught nothing and missed everything this run. Things it would need to flag, from this run's data: registration not yet open at the time of save (run 1, first save), Default Ticket Rule left at Open on a ticketed conference, the workshop being offered to children outside 13-17 (only if the new Extra-requires-ticket-type rule is used), the copy's workshop landing on a Monday, and the promo wording.

## Information needs (grouped)

Unchanged from the first run unless noted. Each line: need, where found, confidence, tool wanted.

### A. Does it exist already?
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Is there already an event with this name or dates? | Events list | High | `list_events(name?, date_range?)` |
| What an event contains | Four admin lists, `?q=` | Medium | `get_event_setup(event_id)` |
| Which build/version of the admin I am using | Not visible; found by `podman top` | Low | A version or build stamp in the admin footer |

### B. Field meaning and allowed values
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Allowed values and defaults of every field | Dropdowns, help text | High | `describe_schema(entity)` |
| What Required / Requires choice / Per attendee do together | Help text plus the public page | Medium | `explain_field(entity, field)` |
| Whether an extra can be limited to ticket types | Form (absent) | High, that it is absent | `describe_schema("extra")` including the gate |

### C. Dates, ages, money and time
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Birthdates for "ages 13-17" | By hand; error message helps | Medium | `age_window_to_birthdates(event_id, min_age, max_age)` |
| Time zone of the date fields | Not stated | Low | Field-level `timezone` |
| What a copy will do to dates and weekdays | After the fact, in the export | Low | `preview_copy(event_id, new_start_date)` |

### D. Relationships
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Limit an add-on to an age band | Not possible | n/a | `explain_modelling(use_case)` or a gate on the Extra |
| Which ticket types a promo affects | Dual list | High | `get_promo(event_id, code)` |

### E. Verifying
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Is the setup consistent | Nothing in the admin | Low | `validate_event(event_id)` (the admin "Check setup", once served) |
| What a family sees and pays | Public form in a browser | High | `preview_form(event_id, profile)`, `preview_price(event_id, family, promo?)` |
| What a copy or edit changed | Export | Medium | `export_event`, `diff_events(a, b)` |

### F. Copying and bulk edits
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Change every price by 10% | By hand, five edits | Medium | `bulk_update_prices(event_id, factor, rounding)` |
| Rename a promo code | Edit the promo | High | `update_promo` |
| Add a choice to an extra | Inline row | Medium | `add_extra_choice(extra_id, label, price_delta?)` |

### Candidate tools

1. `list_events`, `get_event_setup`, `get_registration_status`.
2. `describe_schema(entity)`, `explain_field(entity, field)`.
3. `age_window_to_birthdates` and its inverse.
4. `create_*` and `update_*` for event, ticket type, session, extra (with choices and ticket-type gate), promo code, addressing items by name inside one event.
5. `explain_modelling(use_case)`.
6. `preview_form(event_id, attendee_profile)` and `preview_price(event_id, family, promo_code?)`.
7. `validate_event(event_id)` (what "Check setup" should be, if it reaches the admin).
8. `preview_copy(event_id, new_start_date)` showing weekdays, then `copy_event`.
9. `bulk_update_prices(event_id, factor, rounding)`.
10. `export_event`, `diff_events`.
11. A guard or warning when saving a future registration opening date.

## Counts

- Browser scripts run: about 22 (login, form dumps, saves, final check).
- Screenshots: 4 in `/tmp/trial2/s/` (home, saved event, extra form, final form); I viewed one.
- Saved forms: 1 event (+1 edit), 3 ticket types (+2 failed), 1 session, 2 extras, 1 promo, then run 2: 1 copy, 3 ticket type edits, 2 extra edits, 1 promo edit.
- Documentation read: 1 file (the walkthrough), plus the first run's report for comparison.
- Asked a human or an AI for help: no.
