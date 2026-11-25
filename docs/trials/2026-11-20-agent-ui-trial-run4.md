# Agent-driven UI trial, run 4: event-first forms, scoped pickers, promo messages (2026-11-20)

Short browser trial of the newest `feat/setup-checker` build, by an AI agent in a real browser (Nix Chromium over CDP, closed afterwards). Admin read in Swedish. Browser only: no source, tests, plans or feature-request file; no `manage.py`, no API. `organizer2` (Administratör, not superuser) still worked after the reseed, so I did not recreate it. Invented data only. Nothing was submitted or confirmed on the public form. Time: about 08:31 to 08:45, building plus probing, roughly 8 minutes of tool time.

Event: "Test Workshop Day 2027", id `d762147b-02a1-4f8c-919b-ee196e2ad4ea`, 2027-06-05, opens 2026-11-01, closes 2027-05-22, door rule "everyone attending needs a ticket".

## Verdicts

| # | Item | Verdict |
|---|---|---|
| 1 | Adding an extra, ticket type or promo asks for the event first | **Works** for those three. Session "Add" does not (see below). |
| 2 | Pickers list only that event's rows and are filled on first view | **Works** |
| 3 | Another event's rows can be picked | **Not on the new forms; yes in two places** (session "+" popup, session Add) |
| 4 | An existing row's event can be changed | **No** (field is gone, or shown as read-only text) |
| 5 | Promo message says what the code discounts | **Mostly true; one false case** (code on an inactive ticket type) |
| 6 | Check setup | Works, caught the inactive-only code; location label is cryptic |

## 1. Building the event

- **Event-first step.** Clicking "Lägg till" on Extras, Ticket types or Promo codes opens a page titled "Välj evenemang först" ("Choose event first") with the text "Välj evenemanget detta hör till. Nästa sida visar då bara det evenemangets sessioner och biljettyper." One plain dropdown of all events (newest first, mine on top), one button "Fortsätt". It is a normal select, not the empty-until-you-type autocomplete from earlier runs. After Fortsätt the URL carries `?event=<id>` and the real form opens with the event already chosen. On this form the Event dropdown contains **only** the chosen event.
- **Plain Session add** does not have this step: it is the old form with a plain all-events dropdown. A little inconsistent, but sessions have no pickers that depend on the event.
- **Pickers.** On the extra form: Session select = "Test Workshop Day 2027 - Saturday workshop" only (plus "---------"); "Biljettyper som krävs" dual list = this event's three passes only; both were filled the first time I saw the form, no typing needed. The ticket type form's Sessions list was likewise this event only. The promo form's two dual lists ("applies to" and "unlocks") were also this event only. Session picker is now a plain select, not select2.
- **"Add" from a ticket-type list filtered by the event.** The list's "Lägg till Biljettyp" link carries `_changelist_filters=event__id__exact=...`, and it **skipped the event step** and opened the form with the event already set. "Spara och lägg till ny" also kept the event.
- **Other event's rows.** Not pickable anywhere on the new forms: all lists showed only the chosen event. Not tested: forcing a bad POST (browser only).
- **Changing an existing row's event.** Ticket type, extra and promo change forms have no event field at all (the event is only in the page title). The session change form shows "Evenemang: Test Workshop Day 2027" as plain text. So no, event cannot be edited. A small gap: for the first three, the event name is only visible in the heading.
- **"+" popups on the extra form.** There are "+" add icons next to Event, Session and Biljettyper.
  - Ticket type "+": opened a popup that began with "Välj evenemang först", shown with the **full admin chrome** (sidebar and header) instead of the slim popup layout. After Fortsätt the URL kept `_popup=1` and added `event=`, the slim layout returned, and the event was preselected. I saved "Popup pass" (50 kr) from it and the popup closed by itself. Whether the new row then appeared in the opener's dual list I did not see (I navigated away); unverified.
  - Session "+": opens the plain session form with **all events' names in its Event dropdown and none preselected**. This is where another event's session can still be created from an extra form (it would not show up in the scoped picker, so the organizer would have to understand why).
  - Event "+" (and the pencil/eye next to Event): still present on a field that is now locked to one event. Odd but harmless.

## 2. Promo codes

Created through the new flow (event step once, then `?event=` form): `OPEN10` (10% unrestricted), `ADULT10` (10%, Adult pass), `KID25` (25 kr fixed, Child pass 0-12 and 13-17), `INACT10` (10%, only "Popup pass", which I made inactive first). All saved without complaint, including the one pointing only at an inactive type.

## 3. Public form

Page `http://localhost:5173/register/d762147b-.../`. Family: two adults (adult pass each), "Kid" born 2013-03-10 (14, 13-17 pass), "Minior" born 2018-05-01 (9, 0-12 pass). Subtotal 3 300,00 kr (2 x 1200 + 600 + 300). The public page is Swedish only; I found no language switch, so there is no English text to report.

| Code | Message shown (Swedish, exact) | Summary lines | True? |
|---|---|---|---|
| `OPEN10` | "Koden är tillämpad – 10 % rabatt på summan." | Rabatt -330,00 kr, total 2 970,00 | Yes (10% of 3300) |
| `ADULT10` | "Koden är tillämpad – 10 % rabatt på biljettypen Adult pass." | Rabatt -240,00 kr, total 3 060,00 | Yes (10% of 2 x 1200) |
| `KID25` | "Koden är tillämpad – 25,00 kr rabatt på summan för biljettyperna Child pass 0-12 och Child pass 13-17." | Rabatt -25,00 kr, total 3 275,00 | Yes, once per registration, not per ticket |
| `INACT10` | "Koden är tillämpad." | **No discount line**, total stays 3 300,00 | **No: it says applied, but nothing was discounted** |
| unknown code | "Koden är inte giltig. Kontrollera stavningen, eller kontakta arrangören." | none | Yes |

- **Per ticket or per registration (KID25).** It reads as **per registration**: "25,00 kr rabatt på summan" ("25 kr off the sum"), and the summary shows one -25,00 even though two child tickets qualify. That is consistent and true. A family that read "25 kr on both child passes" as 25 kr per ticket (-50) would still be surprised, but the message does say "på summan". It could say "en gång per anmälan" to remove all doubt. Note this differs from what an organizer meaning "25 kr off each child ticket" would have wanted; there is no way to say that in the form I used.
- **The false case.** A code whose only ticket type is inactive is accepted with a bare "Koden är tillämpad." and zero discount, which is what the family sees. The organizer-side warning (below) exists, the public one does not; it should say something like "gäller inte din anmälan".
- Before this build the message said "10 % rabatt på summan" for a code that only affected the adult line (run 1 to 3); it now names the ticket type.

## 4. Check setup

Events list, tick the row, "Kontrollera upplägg". Result, one warning: `Kampanjkod 'INACT10' (promo_codes[1]): Alla biljettyper som koden hänvisar till är inaktiva.` ("Promo code 'INACT10' (promo_codes[1]): All ticket types the code refers to are inactive.") It names the code and the cause, so it is understandable and it points to the right row. The bracket `promo_codes[1]` is a list index, not a visible number: INACT10 is the fourth code I made, so index 1 is not the creation order and means nothing to an organizer (the name before it saves the day). Nothing else was reported: it did not flag the door rule (I had set it), the future/past opening date, or the inactive "Popup pass" ticket type itself.

## Stuck-point table

| What I tried | What happened | Would have helped |
|---|---|---|
| Session "Add" for the event | No event-first step; plain all-events select | Same step as the other three, or leave it alone but say so |
| "+" next to Biljettyper in the extra form | Popup starts with the event step in full admin chrome, then slim | Preselect the opener's event and skip the step |
| "+" next to Session in the extra form | All events listed, none chosen | Same as above |
| Event "+"/pencil on a locked event field | Still shown | Hide on a locked field |
| Find a row's event on a ticket type / extra / promo edit page | Only in the heading | A read-only "Evenemang:" line like the session form has |
| Inactive-only promo on the public form | "Koden är tillämpad." and no discount | An honest "not applicable" message |
| Read `promo_codes[1]` in Check setup | Index, not a label | Row names with a visible number or title |

## Not tested

- Forcing another event's row by hand (POST), since I was browser-only.
- Whether the popup-created ticket type showed up in the opener's list.
- English public text (none exists).
- The workshop-on-a-Monday copy case from run 3.
