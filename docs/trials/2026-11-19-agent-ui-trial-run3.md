# Agent-driven UI trial, run 3: registration setup on the restarted stack (2026-11-19)

Third pass of the walkthrough (`docs/registration-setup-walkthrough.md`), done by an AI agent in a real browser, this time against `tryggare_web_1` restarted onto the current `feat/setup-checker` code. Earlier reports: `2026-11-19-agent-ui-trial.md` (run 1), `2026-11-19-agent-ui-trial-rerun.md` (stale-server run, called run 2 below because it contained the second set of two runs). Timings are agent wall-clock times, not human times.

## Method and honesty notes

- **Browser.** Nix Chromium 149 over CDP, `uv run --with playwright python`. Chromium died between sessions and I restarted it. It is closed now. Scripts and screenshots are in `/tmp/trial2/`.
- **Account.** `organizer2` (Administratör, staff, not superuser) survived the restart; no recreation was needed. The earlier events also survived. I renamed them in the admin to "Stale run A 2027" and "Stale run B 2028" so that this run's "Test Conference 2027" and "2028" would be unambiguous. This matters because the old events and their ticket types appeared in every dropdown and caused one of the mistakes below.
- **Non-UI reads.** `event_spec export` twice, nothing else. Not read: source, tests, `event_spec/`, plan docs, feature-requests doc, API.
- **Docs.** Walkthrough only.
- **Demo reset.** Reset is hourly at :19. I worked between 19:36 and 19:39, so none hit. Data from the earlier session survived the web restart.
- **Invented data.** Same "Testfamilj" family, `example.invalid` email, no health data. No payment, no email.
- **Language.** The admin stayed Swedish this time (it was already Swedish after the earlier session's language switch), so this run was read in Swedish.

## Run 1: "Test Conference 2027" from scratch

Event id `d15225d0-6800-4fc8-9ad6-5d7312699547`.

| Total | Time to first working ticket | Registration page matched the brief? |
|---|---|---|
| about 50 s of wall clock from first save (19:37:19) to submitted family (19:38:09); about 30 s of that was fixing the setup and about 20 s the final check. The agent already knew the forms, so this is not a human estimate. | about 5 s (adult pass) | Yes |

### What was built

| Brief item | Built as |
|---|---|
| Event, three days | 2027-06-04 to 06-06. Opens 2027-01-15 first, then 2026-11-01 09:00. Closes 2027-05-21 23:59. Default Ticket Rule changed from Open to "Everyone attending needs a ticket" (see Check setup). |
| Adult pass, child 0-12, child 13-17 | As before: 1200 / 300 / 600, capacities 150 / blank / blank, ages as birthdates (2014-06-05; 2009-06-05 to 2014-06-04). |
| Saturday workshop 150, children 13-17 only | **Built exactly as written.** Session (2027-06-05 10:00-12:00) plus an Extra on that session, Applies To Child, with "Biljettyper som krävs" = Child pass 13-17. |
| T-shirt | Extra, 200, per attendee, Requires choice + Required, S/M/L/XL. |
| Promo | `TESTFAMILY`, percent 10, applies to the adult ticket type. |

### Mistakes made, found by Check setup

I made one mistake that the admin accepted without a word: when picking the workshop's session I typed "Saturday" and clicked the first result containing "2027". That was the **stale event's** session, not this event's. The extra saved cleanly. Check setup (below) caught it. This is the same wrong-event-in-a-dropdown trap as the previous runs, now caught after the fact.

### "Check setup" in run 1

How to run it: Events list, tick the row, choose the action "Kontrollera upplägg" (Check setup), Go. The result renders as a page headed "Kontrollera upplägg" plus the event name, with sections "Fel" (errors), "Varningar" (warnings), and a message at the top. I ran it three times:

1. **After building everything (opens-at in the future 2027-01-15).** Reported one **error**: `(event): "Saturday workshop" (tillval) refererar till pass "Saturday workshop", som hör till ett annat evenemang.` ("(extra) refers to session 'Saturday workshop', which belongs to another event".) Correct, and it is the real mistake. But the wording is hard to act on: both the extra and the session are called "Saturday workshop", the other event is not named, and it says "(event)" in the location. "Pass" is the Swedish word for session here, which I only knew from context; elsewhere in the same admin "pass" is also the English "Child pass" ticket name. I fixed it by opening the extras list (which has Event and Session columns, where the mismatch was visible) and re-picking the session. It helped: without it I would have shipped it and found out only from the final check, if at all.
2. **After the fix.** One **warning**: `Evenemang (event.ticket_rule_default): Incheckning är öppen för alla som standard, men evenemanget säljer biljetter, så ingen behöver biljett vid dörren. Avsiktligt?` ("Check-in is open to everyone by default, but the event sells tickets, so nobody needs a ticket at the door. Intentional?") Clear and useful: it is the risky default found in run 1. The location label `event.ticket_rule_default` is a field path, not the form label ("Standardregel för biljetter"); I had to match it by eye. I set the rule to "Everyone attending needs a ticket" and moved on.
3. **After setting opens-at to the past and the ticket rule.** "Inga problem hittades." ("No problems found.")

What it did **not** say: nothing about the opening date being in the future (when I first saved 2027-01-15 and the public page said "not open yet"). The first run's problem there is unchanged. It also reported nothing when everything was fine except a bare "no problems", with no list of what was checked.

### Final check on the frontend

Page `http://localhost:5173/register/d15225d0-.../`. Same family as before: parent (adult pass, T-shirt M), "Kid" born 2013-03-10 (14; 13-17 pass, T-shirt S, workshop), "Minior" born 2018-05-01 (9; 0-12 pass, T-shirt L).

- **Prices.** 1200 + 200 + 600 + 200 + 150 + 300 + 200 = 2850, TESTFAMILY -120 (10% of the adult line only), total 2730. The confirmation (reference `7C2AGKSW`) shows 2 730,00 kr. Matches.
- **Ticket choices by age.** As before: wrong band disabled with "(13-17 år)" or "(upp till 12 år)".
- **Saturday workshop.**
  - 14-year-old with the 13-17 pass: checkbox offered and enabled, and I submitted with it checked. It appears on the confirmation next to "Kid".
  - 9-year-old with the 0-12 pass: the workshop is still **listed**, but the checkbox is **disabled** with the note "Kräver biljett: Child pass 13-17". It could not be selected.
  - Before any child ticket is chosen, the workshop checkbox is enabled for a child of any age. Only choosing the ticket disables it.
  - So "offered only to 13-17" is met in effect, by gating on the chosen ticket rather than on age. The outcome is right, but a family still sees a greyed-out workshop on a 9-year-old.
- **T-shirt.** Offered to the parent and both children, marked required.
- **Promo.** Applied to the adult line only. The message still says "10 % rabatt på summan" (10% off the total), which is misleading.
- **Submit.** Reached "Bekräfta din e-post". Nothing was confirmed or sent.

Snapshot: `docs/trials/2026-11-19-run3-run1-export.json` (taken after the Check setup fixes, before registering). The workshop extra's `ticket_types` is `["child-pass-13-17"]` in it.

## Run 2: "Test Conference 2028" from a copy

Event id `f478364b-6a6a-4870-a4e7-35f351a2bf1e`.

| Total | Time to first working ticket | Registration page matched? |
|---|---|---|
| about 18 s (19:38:21 to 19:38:39): copy, 7 edits, 2 Check setup runs | n/a | Not tested in the frontend (opens 2027-11-02); checked through the export. |

- **Copy.** Same flow, start date 2028-06-04 (one year later, a Sunday), as asked.
- **What the copy did.** Opens 2027-11-02 09:00, closes 2028-05-21 23:59; age windows recomputed (0-12 min 2015-06-05; 13-17 2010-06-05 to 2015-06-04); capacity 150 kept; Default Ticket Rule "all" kept; workshop session moved to 2028-06-05, **a Monday**.
- **The gate on copy.** The copied workshop extra is scoped to the 2028 session and its required ticket type is **"Test Conference 2028 - Child pass 13-17"**, the 2028 ticket type, not the 2027 one (seen on the extra's edit form and in the export as `child-pass-13-17`). Copy remaps the gate correctly.
- **Edits.** Adult 1320, 0-12 330, 13-17 660, workshop 165, T-shirt 220 (all +10%, whole SEK), promo `TESTFAMILY28`, XXL added as a fifth choice. Choice price deltas are 0, so no rounding needed. Saving the 13-17 ticket type and the workshop extra, which are linked by the gate, raised no complaints.
- **"Check setup".** Run twice (right after the copy and after the edits): both "Inga problem hittades." It did **not** flag the workshop on a Monday. It also did not flag registration opening 2027-11-02 for a June 2028 event (that is fine), and it said nothing about the workshop gate surviving the copy (it did, so correctly nothing).
- **Snapshot.** `docs/trials/2026-11-19-run3-run2-export.json`.

## Stuck-point table

| Time | What I was trying to do | Where I looked | What I tried | What happened | Would have helped |
|---|---|---|---|---|---|
| 19:37 | Pick the workshop's session on the extra | Extra form, Session select2 | Typed "Saturday", clicked the first result containing "2027" | Picked the stale event's session; the admin saved it without a warning. Dropdowns list every event's sessions and ticket types, with old events side by side. | Filter by the chosen event, or reject cross-event pairs on save |
| 19:37 | Understand the Check setup error | Check setup result | Read the message, then the extras list | Message names "Saturday workshop" twice, not the other event; location is "(event)". Fixed after finding the Event/Session columns in the extras list. | Name the other event; a link to the record |
| 19:37 | Decide what the ticket-rule warning wants | Check setup result | Changed Default Ticket Rule to "Everyone attending" | Worked, but the brief does not say which door rule is right | Nothing missing; the warning is good |
| 19:37 | Choose the opens-at date | Event form | Future date, then the past | Same as before: no warning on save, no warning from Check setup. | Check setup note: "registration not open yet" |
| 19:37 | Pick events in select2 | Event field | Typed the name | Still empty until you type (unchanged). | Short list on focus |
| 19:37 | Age bounds | Ticket type form | Birthdates by hand | Unchanged; the anniversary error is helpful but the arithmetic is mine. | Age-in-years entry |
| 19:38 | Copy one year forward | Copy form | Typed 2028-06-04 | No preview; the Saturday workshop lands on a Monday and Check setup is silent. | Weekday preview, or a Check setup warning |

## Deviations from the brief

- **Workshop 13-17 only.** Now built as written, via the extra's required ticket type. The frontend enforces it by the child's chosen ticket (a 9-year-old on the 0-12 pass sees it disabled). There is still no age field on the extra itself.
- **Registration opens "on a date you choose".** Same trap as before: a future date blocks the page, with no warning.
- **Promo "for families registering together".** No field. Unchanged.
- **Door rule.** I set "Everyone attending needs a ticket" in response to the warning. The brief did not specify it.
- **Run 2 start date.** Exactly one year later (Sunday), so the copy's Saturday workshop is on a Monday.

## Labels and messages that misled

- Check setup error uses "pass" for session. In the same admin "pass" is also in ticket type names ("Child pass 0-12"); and the message says "(event)" where it means the extra.
- Check setup location `event.ticket_rule_default` is a field path, not the label shown on the form.
- "10 % rabatt på summan" on a promo that only discounts the adult line.
- The workshop is shown but disabled for the 9-year-old, with "Kräver biljett: Child pass 13-17", which tells the family what to buy but not that the child is too young for it.
- The "Biljettyper som krävs" widget lists every event's ticket types (including the stale events'), though its help text says only the extra's own event's are valid. A wrong pick presumably fails on save (I did not test it).
- The copy form says dates shift "lika många dagar", but ages are recomputed on the new start date.
- Unchanged: required/Requires choice wording, Hidden/Active, all-events dual lists, doubled `_old` widgets.

## Things I did twice

- The Event opens-at date.
- The workshop's session (wrong event first, then fixed).

## Compared with runs 1 and 2

Marks: fixed, better, unchanged, worse. Run 1 is `2026-11-19-agent-ui-trial.md`; run 2 is the stale-server report.

### Stuck points

| Earlier stuck point | Now | Evidence |
|---|---|---|
| No way to check the setup (run 1: only the CLI `validate`; run 2: action absent) | **Fixed** | "Kontrollera upplägg" in the Events actions. It found a real error and a real risky default. |
| Age-limited add-on impossible | **Fixed** (by a ticket-type gate rather than age) | Extra form field "Biljettyper som krävs"; 14-year-old can pick the workshop, the 9-year-old's is disabled. |
| Session bundle ticket as add-on does not work | **Fixed** | Not needed; the gate removes the detour. |
| Event select empty until you type | Unchanged | Same select2. |
| Wrong-event pick (sessions, ticket types) | **Unchanged**, but now detected after the fact | Admin accepted a session from another event; Check setup flagged it. |
| Age bounds need hand-computed birthdates | Better | Anniversary errors explain the rule with an example; copy recomputes windows. Entry still by date. |
| Future opens-at blocks page, no warning | Unchanged | No warning on save or from Check setup. |
| Sessions / ticket types lists show every event | Unchanged | Same; now worse in practice because the stale events were still around. |
| "Required" help text | Unchanged | Same wording. |
| Copy form has no date preview | Unchanged | Workshop lands on a Monday, silent (also run 2). |

### Deviations

| Earlier deviation | Now | Evidence |
|---|---|---|
| Workshop 13-17 only | **Fixed** | As above, built as written. |
| Opens-at in the past conflicts with `validate` (run 1) | Fixed for this run, by a different route | Check setup raised nothing for a past opens-at on a registered event. I did not run `validate`. |
| Promo "for families together" | Unchanged | No field. |
| Door rule default Open on a ticketed event | **Fixed** (surfaced) | Check setup warns and asks "Avsiktligt?". The default itself is still Open. |
| Leftover inactive bundle type in the copy | Fixed | None built. |

### Run 2 versus run 3

- Check setup: absent in run 2, found three real things in run 3.
- Ticket types, copy, edits: no change in behaviour. Copy remaps the gate to the new event's ticket type.
- Language: stayed Swedish this time; the flip is not reproduced because it had already flipped.

## What Check setup caught and missed

- **Caught:** an extra pointing at another event's session (error); a ticketed event with the door rule left at Open (warning).
- **Missed:** future registration opening on the live event; workshop on a Monday after a one-year copy; no age window gap check was exercised (my bands cover 0-17 with no gaps, so nothing to catch); the Swedish word "pass" in its own message mixes with the English ticket names.
- **Style:** a "no problems" result is a bare sentence; a short list of what was checked would be more convincing.

## Information needs (grouped)

### A. Does it exist already?
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Existing events and their status | Events list | High | `list_events` |
| Event contents | Four admin lists | Medium | `get_event_setup(event_id)` |

### B. Field meaning
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Whether an extra can be limited to ticket types | Form field and its help text | High | `describe_schema("extra")` |
| What the checker's field paths mean | Guessed from the form | Medium | Use form labels in messages |

### C. Dates and ages
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Birthdates for age bands | By hand | Medium | `age_window_to_birthdates` |
| What a copy does to dates and weekdays | After the fact | Medium | `preview_copy` with weekdays |

### D. Relationships
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Which event a session/ticket type belongs to when picking it | Select text, with old events present | Low | Event-filtered pickers |

### E. Verifying
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| Is the setup consistent | Check setup | Medium-high | `validate_event(event_id)` (same as the admin action) |
| What a family sees and pays | Public form | High | `preview_form`, `preview_price` |
| Does it match after copy/edit | Export | Medium | `export_event`, `diff_events` |

### F. Copying
| Need | Found | Confidence | Wanted tool |
|---|---|---|---|
| +10% on all prices | By hand, 5 edits | Medium | `bulk_update_prices(event_id, factor, rounding)` |
| Rename code, add choice | Edit forms | High | `update_promo`, `add_extra_choice` |

### Candidate tools
1. `list_events`, `get_event_setup`, `describe_schema(entity)`.
2. `create_*` / `update_*` addressing items by name inside one event (so a wrong-event pick cannot happen), including the extra's ticket-type gate.
3. `validate_event` returning the same errors and warnings as Check setup, with record links and both events named.
4. `age_window_to_birthdates` and its inverse.
5. `preview_form` and `preview_price`.
6. `preview_copy(event_id, new_start_date)` with weekdays, and a Check setup rule for "session weekday changed on copy".
7. `bulk_update_prices`.
8. `export_event`, `diff_events`.
9. A Check setup note for a registration opening date in the future.

## Counts

- Browser scripts run: about 14.
- Screenshots: 5 in `/tmp/trial2/s/`; viewed none this time, reading page text.
- Saved forms: 1 event (+1 edit), 3 ticket types, 1 session, 3 extras (+1 fix), 1 promo, then run 2: 1 copy, 3 ticket type edits, 2 extra edits, 1 promo edit. Also renamed 2 stale events.
- Check setup runs: 5 (3 in run 1, 2 in run 2).
- Documentation read: the walkthrough only.
- Asked a human or an AI for help: no.
