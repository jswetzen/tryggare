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
    RegistrationExtraSelectionPayload
  } from '$lib/api/types';
  import ConsentCapture, { type HealthInfoStatus } from '$lib/components/checkin/ConsentCapture.svelte';
  import EyebrowLabel from '$lib/components/ui/EyebrowLabel.svelte';
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
    extraSelections: Record<string, ExtraSelectionState>;
  }

  interface ChildRow {
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
    ticketTypeId: string;
    extraSelections: Record<string, ExtraSelectionState>;
  }

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
      relationship_type: 'OTHER',
      allergies: '',
      notes: '',
      healthInfoStatus: 'none',
      consentNoticeShared: false,
      ticketTypeId: '',
      extraSelections: {}
    };
  }

  function emptyChild(): ChildRow {
    return {
      first_name: '',
      last_name: '',
      birthdate: '',
      allergies: '',
      notes: '',
      healthInfoStatus: 'none',
      consentNoticeShared: false,
      ticketTypeId: '',
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

  let error = $state('');
  // The raw DRF error body from a failed submit, e.g.
  // {"children": {"1": ["..."]}} for a per-attendee ticket-type failure
  // (see registrations/views.py::submit_registration). Drives the inline
  // per-attendee errors below; `error` above carries the banner text.
  let errorDetails = $state<unknown>(null);
  let errorBannerEl = $state<HTMLElement | null>(null);
  let submitting = $state(false);
  let submitted = $state(false);
  let referenceCode = $state<string | null>(null);

  // Scroll/focus the failure banner into view on every new error — on this
  // 2000+px page a failed submit otherwise looks like nothing happened from
  // the submit button at the bottom (see build's blocker #2).
  $effect(() => {
    if (error && errorBannerEl) {
      errorBannerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      errorBannerEl.focus();
    }
  });

  function childAgeError(index: number): string | null {
    return extractFieldError(errorDetails, 'children', index);
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
    return (
      selections[extra.id] ?? {
        selected: extra.required || extra.default_selected,
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

  function suggestChildTicketType(child: ChildRow) {
    if (!eventInfo || child.ticketTypeId || !child.birthdate) return;
    const candidates = applicableTicketTypes(true).filter(
      (tt) =>
        (!tt.min_birthdate || child.birthdate >= tt.min_birthdate) &&
        (!tt.max_birthdate || child.birthdate <= tt.max_birthdate)
    );
    // Prefer a type with an actual age window over one with none — an
    // unbounded "either" type (e.g. "All inclusive", no age limit) always
    // matches and must not shadow a more specific age-tiered type (e.g.
    // "0-6 år") just because it happens to sort first. Only fall back to
    // an unbounded type when nothing more specific matches.
    const bounded = candidates.find((tt) => tt.min_birthdate || tt.max_birthdate);
    const match = bounded ?? candidates[0];
    if (match) child.ticketTypeId = match.id;
  }

  function buildExtraSelections(
    selections: Record<string, ExtraSelectionState>,
    extras: RegistrationExtraInfo[]
  ): RegistrationExtraSelectionPayload[] {
    const result: RegistrationExtraSelectionPayload[] = [];
    for (const extra of extras) {
      // Use extraState's default_selected fallback, not a raw lookup — an
      // opt-out-by-default extra (case 2.1) the guardian never explicitly
      // toggled must still submit as selected, matching what the checkbox
      // displays. Reading selections[extra.id] directly here would drop it
      // from the payload while the UI still showed it checked.
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

  async function checkPromoCode() {
    const code = promoCode.trim();
    promoCodeError = '';
    promoCodeValidation = null;
    if (!code || !eventInfo) return;

    promoCodeChecking = true;
    try {
      const result = await registrationApi.validatePromoCode(eventId, code);
      if (!result.valid) {
        promoCodeError = $t('register.promoCodeInvalid');
        return;
      }
      promoCodeValidation = result;
      // Reveal any is_hidden ticket types this code unlocks (e.g. VIP) by
      // merging them into the local list — applicableTicketTypes/
      // suggestChildTicketType then pick them up with no further changes.
      const unlocked = result.unlocks_ticket_types ?? [];
      const existingIds = new Set(eventInfo.ticket_types.map((tt) => tt.id));
      const newlyUnlocked = unlocked.filter((tt) => !existingIds.has(tt.id));
      if (newlyUnlocked.length > 0) {
        eventInfo = { ...eventInfo, ticket_types: [...eventInfo.ticket_types, ...newlyUnlocked] };
      }
    } catch (err) {
      console.error('Promo code validation failed:', err);
      promoCodeError = $t('register.promoCodeInvalid');
    } finally {
      promoCodeChecking = false;
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

    if (isPreview) return;

    if (!contactEmail.trim()) {
      error = $t('register.contactEmailRequired');
      return;
    }

    for (const child of children) {
      if (!child.first_name.trim() || !child.last_name.trim() || !child.birthdate.trim()) {
        error = $t('checkin.allChildrenRequired');
        return;
      }
      if (child.healthInfoStatus === 'consented' && !child.consentNoticeShared) {
        error = $t('checkin.healthConsentRequired');
        return;
      }
    }

    const validParents = parents.filter((p) => p.first_name.trim().length > 0);

    if (children.length === 0 && validParents.length === 0) {
      error = $t('checkin.atLeastOneMemberRequired');
      return;
    }

    for (const p of validParents) {
      if (p.phone && !isValidPhone(p.phone)) {
        error = $t('checkin.invalidPhone');
        return;
      }
      if (p.healthInfoStatus === 'consented' && !p.consentNoticeShared) {
        error = $t('register.adultHealthConsentRequired');
        return;
      }
    }

    const requiresTicketType = !!eventInfo && eventInfo.ticket_types.length > 0;
    if (requiresTicketType) {
      const missing =
        validParents.some((p) => !p.ticketTypeId) || children.some((c) => !c.ticketTypeId);
      if (missing) {
        error = $t('register.ticketTypeRequired');
        return;
      }
    }

    const missingRequiredChoice =
      validParents.some((p) => requiredChoiceMissing(p.extraSelections, applicablePersonExtras(false))) ||
      children.some((c) => requiredChoiceMissing(c.extraSelections, applicablePersonExtras(true))) ||
      requiredChoiceMissing(registrationExtraSelections, registrationExtras());
    if (missingRequiredChoice) {
      error = $t('register.requiredExtraMissing');
      return;
    }

    const statusMap: Record<HealthInfoStatus, HealthConsentStatus> = {
      none: 'not_applicable',
      consented: 'granted',
      declined: 'declined'
    };

    submitting = true;
    try {
      const response = await registrationApi.submit({
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
        website
      });
      referenceCode = response.reference_code;
      submitted = true;
    } catch (err) {
      console.error('Registration submission failed:', err);
      const apiError = err as ApiError;
      errorDetails = apiError.details ?? null;
      // Prefer the server's specific reason (e.g. "This attendee doesn't
      // meet this ticket type's age requirements.") — extracted straight
      // from apiError.details rather than apiError.message, since the
      // latter already falls back to the raw HTTP status text
      // (client.ts::extractErrorMessage's own fallback) and that's exactly
      // the non-specific case this must not surface as if it were real
      // information.
      error = extractErrorMessage(apiError.details, '') || $t('register.submitError');
    } finally {
      submitting = false;
    }
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
  {:else if submitted}
    <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center">
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.successTitle')}</h1>
      <p class="text-neutral-700 mb-4">
        {$t('register.successMessage', { values: { email: contactEmail.trim() } })}
      </p>
      {#if referenceCode}
        <p class="text-sm text-neutral-500">
          {$t('register.referenceCode', { values: { code: referenceCode } })}
        </p>
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
      class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm"
      data-testid="register-form"
    >
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

      {#if error}
        <div
          class="mb-4 p-2 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm focus:outline-none focus:ring-2 focus:ring-danger-500"
          role="alert"
          tabindex="-1"
          bind:this={errorBannerEl}
        >
          {error}
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
          {$t('register.contactEmail')} *
        </label>
        <input
          id="contact-email"
          type="email"
          bind:value={contactEmail}
          placeholder={$t('register.contactEmailPlaceholder')}
          required
          class="w-full px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
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
                    {$t('checkin.parentFirstName')} *
                  </label>
                  <input
                    id={`parent-first-name-${index}`}
                    type="text"
                    bind:value={parent.first_name}
                    placeholder={$t('checkin.parentFirstNamePlaceholder')}
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
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <label for={`parent-relationship-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.relationshipType')}
                  </label>
                  <select
                    id={`parent-relationship-${index}`}
                    bind:value={parent.relationship_type}
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="MOM">{$t('checkin.relationshipMom')}</option>
                    <option value="DAD">{$t('checkin.relationshipDad')}</option>
                    <option value="GUARDIAN">{$t('checkin.relationshipGuardian')}</option>
                    <option value="OTHER">{$t('checkin.relationshipOther')}</option>
                  </select>
                </div>
                <div>
                  <label for={`parent-phone-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.parentPhone')}
                  </label>
                  <input
                    id={`parent-phone-${index}`}
                    type="tel"
                    bind:value={parent.phone}
                    placeholder={$t('checkin.parentPhonePlaceholder')}
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
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
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              {#if applicableTicketTypes(false).length > 0}
                <div class="mt-2">
                  <label for={`parent-ticket-type-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('register.ticketTypeLabel')} *
                  </label>
                  <select
                    id={`parent-ticket-type-${index}`}
                    bind:value={parent.ticketTypeId}
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    data-testid={`parent-ticket-type-${index}`}
                  >
                    <option value="">{$t('register.ticketTypePlaceholder')}</option>
                    {#each applicableTicketTypes(false) as ticketType (ticketType.id)}
                      <option value={ticketType.id}>{ticketType.name} — {formatCurrency(ticketType.price)} kr</option>
                    {/each}
                  </select>
                  {#if ticketCompositionWarning(parent.ticketTypeId)}
                    <p class="mt-1 text-xs text-danger-700">{ticketCompositionWarning(parent.ticketTypeId)}</p>
                  {/if}
                </div>
              {/if}

              {#each applicablePersonExtras(false).filter((extra) => extra.required) as extra (extra.id)}
                {@const state = extraState(parent.extraSelections, extra)}
                <div class="mt-2">
                  <div class="block text-xs text-neutral-600 mb-1">
                    {extra.name} {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''} *
                  </div>
                  {#if extra.requires_choice}
                    <div class="flex items-center gap-3 flex-wrap">
                      {#each extra.choices as choice (choice.id)}
                        <label class="flex items-center gap-1 text-sm text-neutral-700">
                          <input
                            type="radio"
                            name={`extra-${extra.id}-parent-${index}`}
                            checked={state.choiceId === choice.id}
                            on:change={() => setExtraChoice(parent.extraSelections, extra, choice.id)}
                          />
                          {choice.label}{choice.price_delta !== '0.00' ? ` (+${formatCurrency(choice.price_delta)} kr)` : ''}
                        </label>
                      {/each}
                    </div>
                  {/if}
                </div>
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
                    {$t('checkin.childFirstName')} <span class="text-danger-600">*</span>
                  </label>
                  <input
                    id={`child-first-name-${index}`}
                    type="text"
                    bind:value={child.first_name}
                    placeholder={$t('checkin.childFirstNamePlaceholder')}
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  />
                </div>

                <div>
                  <label for={`child-last-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.childLastName')} <span class="text-danger-600">*</span>
                  </label>
                  <input
                    id={`child-last-name-${index}`}
                    type="text"
                    bind:value={child.last_name}
                    placeholder={$t('checkin.childLastNamePlaceholder')}
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  />
                </div>

                <div>
                  <label for={`child-birthdate-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.childBirthdate')} <span class="text-danger-600">*</span>
                  </label>
                  <input
                    id={`child-birthdate-${index}`}
                    type="date"
                    bind:value={child.birthdate}
                    on:change={() => suggestChildTicketType(child)}
                    lang={$locale === 'sv' ? 'sv-SE' : 'en-US'}
                    max={todayIso}
                    min={minBirthdateIso}
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  />
                  <p class="mt-1 text-xs text-neutral-500">{$t('register.birthdateFormatHint')}</p>
                </div>

                {#if applicableTicketTypes(true).length > 0}
                  <div>
                    <label for={`child-ticket-type-${index}`} class="block text-xs text-neutral-600 mb-1">
                      {$t('register.ticketTypeLabel')} <span class="text-danger-600">*</span>
                    </label>
                    <select
                      id={`child-ticket-type-${index}`}
                      bind:value={child.ticketTypeId}
                      class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                      data-testid={`child-ticket-type-${index}`}
                    >
                      <option value="">{$t('register.ticketTypePlaceholder')}</option>
                      {#each applicableTicketTypes(true) as ticketType (ticketType.id)}
                        <option value={ticketType.id}>{ticketType.name} — {formatCurrency(ticketType.price)} kr</option>
                      {/each}
                    </select>
                    {#if ticketCompositionWarning(child.ticketTypeId)}
                      <p class="mt-1 text-xs text-danger-700">{ticketCompositionWarning(child.ticketTypeId)}</p>
                    {/if}
                    {#if childAgeError(index)}
                      <p class="mt-1 text-xs text-danger-700" data-testid={`child-age-error-${index}`}>
                        {childAgeError(index)}
                      </p>
                    {/if}
                  </div>
                {/if}

                {#each applicablePersonExtras(true).filter((extra) => extra.required) as extra (extra.id)}
                  {@const state = extraState(child.extraSelections, extra)}
                  <div class="md:col-span-2">
                    <div class="block text-xs text-neutral-600 mb-1">
                      {extra.name} {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''} *
                    </div>
                    {#if extra.requires_choice}
                      <div class="flex items-center gap-3 flex-wrap">
                        {#each extra.choices as choice (choice.id)}
                          <label class="flex items-center gap-1 text-sm text-neutral-700">
                            <input
                              type="radio"
                              name={`extra-${extra.id}-child-${index}`}
                              checked={state.choiceId === choice.id}
                              on:change={() => setExtraChoice(child.extraSelections, extra, choice.id)}
                            />
                            {choice.label}{choice.price_delta !== '0.00' ? ` (+${formatCurrency(choice.price_delta)} kr)` : ''}
                          </label>
                        {/each}
                      </div>
                    {/if}
                  </div>
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
        <div class="mb-4">
          <div class="block text-xs text-neutral-600 mb-1">
            {extra.name} {extra.price !== '0.00' ? `(${formatCurrency(extra.price)} kr)` : ''} *
          </div>
          {#if extra.requires_choice}
            <div class="flex items-center gap-3 flex-wrap">
              {#each extra.choices as choice (choice.id)}
                <label class="flex items-center gap-1 text-sm text-neutral-700">
                  <input
                    type="radio"
                    name={`extra-${extra.id}-registration`}
                    checked={state.choiceId === choice.id}
                    on:change={() => setExtraChoice(registrationExtraSelections, extra, choice.id)}
                  />
                  {choice.label}{choice.price_delta !== '0.00' ? ` (+${formatCurrency(choice.price_delta)} kr)` : ''}
                </label>
              {/each}
            </div>
          {/if}
        </div>
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
          <div class="flex items-center gap-2">
            <input
              type="text"
              bind:value={promoCode}
              on:input={() => {
                // Editing the code invalidates whatever "Använd" last
                // checked — without this, clearing the field leaves the
                // stale invalid-code message on screen with no way to
                // dismiss it (Använd stays disabled on an empty field).
                promoCodeError = '';
                promoCodeValidation = null;
              }}
              placeholder={$t('register.promoCodePlaceholder')}
              class="flex-1 px-3 py-2 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
              data-testid="register-promo-code-input"
            />
            <button
              type="button"
              on:click={checkPromoCode}
              disabled={promoCodeChecking || !promoCode.trim()}
              class="px-3 py-2 text-sm font-semibold border border-neutral-300 rounded hover:bg-neutral-50 disabled:opacity-50"
              data-testid="register-promo-code-apply"
            >
              {promoCodeChecking ? $t('register.promoCodeChecking') : $t('register.promoCodeApply')}
            </button>
          </div>
          {#if promoCodeValidation?.valid}
            <p class="mt-1 text-xs text-success-700" data-testid="register-promo-code-applied">
              {$t('register.promoCodeApplied')}
            </p>
          {:else if promoCodeError}
            <p class="mt-1 text-xs text-danger-700">{promoCodeError}</p>
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
