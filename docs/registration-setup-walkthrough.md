# Walkthrough: set up a conference registration in Tryggare

Purpose: measure how hard it is for an organizer to build a registration form in Tryggare, without help from a developer or an AI assistant. Time it, and write down every place you get stuck. The result is the Tryggare half of the baseline in `docs/roadmap/registration_form_builder.md`.

This is a test of the product, not of you. If something is hard, that is the finding.

## Ground rules

1. **Use the dev or demo stack only.** Do not use the production instance or real event data.
2. **Use invented people and places.** Names like "Test Family" and "Test Camp". No real names, personnummer, contact details, or health or allergy information, not even as examples. This is the same rule the product applies to its own AI features (see "Personal data is forbidden" in the roadmap doc).
3. **Do not ask an AI assistant or a developer for help.** If you get stuck, write the stuck point down, then continue. Note it if you ask anyone at all, and what you asked.
4. **Stop after 60 minutes** unless you are close to finished. Record where you were.

## Before you start

- Start the dev stack. Frontend at `http://localhost:5173`, backend at `http://localhost:8000` (`docker-compose.yml`; see `CLAUDE.md`).
- Log in to Django admin at `http://localhost:8000/admin/` with the demo account. The demo account is documented in the project `CLAUDE.md` as dev-only.
- Write down the time you start: ____

## The brief

Build a registration for a fictional conference, "Test Conference 2027", with these rules:

- **Event:** one event, three days. Registration opens on a date you choose and closes two weeks before the event.
- **Tickets:**
  - Adult conference pass, price 1 200 SEK, for parents.
  - Child pass for ages 0 to 12, price 300 SEK.
  - Child pass for ages 13 to 17, price 600 SEK.
  - Child tickets are for children, adult tickets are for parents.
- **Session add-on:** a Saturday workshop, price 150 SEK, for children aged 13 to 17 only.
- **Extra:** a t-shirt, price 200 SEK, one per person, with a size choice (S, M, L, XL). Required if the person is buying a ticket.
- **Promo code:** `TESTFAMILY`, 10 percent off, valid for adult tickets only, for families registering together.
- **Capacity:** the adult pass has 150 places. Leave the child passes unlimited.

Do not try to be clever. If the brief can't be built exactly as written, record which part and what you did instead.

## What to record

Fill in a line for every stuck point:

| Time | What I was trying to do | Where I looked | What I tried | What happened | Would have helped |
|---|---|---|---|---|---|
| | | | | | |

Also record:
- **Total time** to a finished setup: ____
- **Time to first working ticket**: ____
- **Did the registration page show what you expected?** Yes / No / Partly
- **Did you have to read documentation?** Which?
- **Anything you did twice** because the first attempt was not saved or was not visible where you expected.
- **Anything you were not sure was correct**, such as price, age band, or whether a promo code applied.

## Final check

Open the public registration page for the event on the frontend and register one invented family, with invented details, to see the flow end to end. Record:
- whether the price shown matches what you set up;
- whether the child and adult tickets appear as you expected;
- whether the Saturday add-on and t-shirt choice are offered only where you set them up.

Stop there. Do not confirm any real payment or send any real email.

## Where the documentation is

There is no organizer setup guide yet. This walkthrough is the first attempt to write one, and the gap is itself a finding. The following are the closest sources. Note whether you read them, and whether they helped.

- `docs/specification.md`, "Data Model" (lines 8 to 80): what events, sessions, and tickets are.
- `docs/roadmap/staff_ui_plan.md`: the admin is the organizer UI. The plan says the admin was never configured for this use, and that a 30-minute persona test found the same kind of problem.
- `docs/roadmap/event_registration_and_mailing.md`: how self-serve registration is meant to work. Its status section says phase 1 (free-event registration) is built, and phase 2 (payment) is not.
- `docs/roadmap/event_registration_ux_case_catalog.md`, Part 2: the intended parent-facing flow. Read it for what the parent should see, not for how to configure the admin. It is long: 1900 lines.
- `docs/deployment.md`: how the stack is run, for the dev-environment setup only.

Relevant admin models for organizers, from `backend/events/models.py`:
- `Event`: registration opens and closes (`registration_opens_at`, `registration_closes_at`).
- `TicketType`: price, who it applies to, capacity, hidden or not, active or not.
- `Session` and session ticket types.
- `Extra`: price, who it applies to, per attendee, required, default selected, with `ExtraChoice` for choices.
- `PromoCode`: active or not, and which ticket types it applies to.

Please note where the admin labels, field help, or error messages did not match what you expected, since those are the highest-value findings.

## After the run

Send the filled-in table and totals to whoever is running the baseline. Do not paste anything from the dev stack that contains invented personal details.
