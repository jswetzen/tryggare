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
  import type {
    RegistrationEventInfo,
    RegistrationExtraInfo,
    RegistrationExtraSelectionPayload
  } from '$lib/api/types';
  import ConsentCapture, { type HealthInfoStatus } from '$lib/components/checkin/ConsentCapture.svelte';
  import { isValidPhone } from '$lib/utils/phone';

  type HealthConsentStatus = 'not_applicable' | 'granted' | 'declined';

  interface ExtraSelectionState {
    selected: boolean;
    choiceId: string;
    quantity: number;
  }

  interface ParentRow {
    first_name: string;
    phone: string;
    email: string;
    relationship_type: string;
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

  function emptyParent(): ParentRow {
    return {
      first_name: '',
      phone: '',
      email: '',
      relationship_type: 'OTHER',
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

  let error = $state('');
  let submitting = $state(false);
  let submitted = $state(false);
  let referenceCode = $state<string | null>(null);

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
    error = '';

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
          phone: p.phone.trim(),
          email: p.email.trim(),
          relationship_type: p.relationship_type,
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
        website
      });
      referenceCode = response.reference_code;
      submitted = true;
    } catch (err) {
      console.error('Registration submission failed:', err);
      error = $t('register.submitError');
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
      <h1 class="text-2xl font-bold text-neutral-900 mb-1">
        {$t('register.heading', { values: { event: eventInfo.name } })}
      </h1>
      <p class="text-sm text-neutral-600 mb-1">{$t('register.introText')}</p>
      {#if eventInfo.is_paid && eventInfo.price && eventInfo.ticket_types.length === 0}
        <p class="text-sm font-semibold text-neutral-700 mb-4">
          {$t('register.eventPriceNotice', { values: { amount: eventInfo.price, currency: eventInfo.currency } })}
        </p>
      {/if}

      {#if error}
        <div class="mb-4 p-2 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
          {error}
        </div>
      {/if}

      <!-- Honeypot field: visually hidden, never shown to real users -->
      <div class="absolute -left-[9999px]" aria-hidden="true">
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
                  <label for={`parent-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                    {$t('checkin.parentName')} *
                  </label>
                  <input
                    id={`parent-name-${index}`}
                    type="text"
                    bind:value={parent.first_name}
                    placeholder={$t('checkin.parentNamePlaceholder')}
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
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
              </div>
              <div class="grid grid-cols-2 gap-2">
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
                      <option value={ticketType.id}>{ticketType.name} — {ticketType.price} kr</option>
                    {/each}
                  </select>
                </div>
              {/if}

              {#each applicablePersonExtras(false).filter((extra) => extra.required) as extra (extra.id)}
                {@const state = extraState(parent.extraSelections, extra)}
                <div class="mt-2">
                  <div class="block text-xs text-neutral-600 mb-1">
                    {extra.name} {extra.price !== '0.00' ? `(${extra.price} kr)` : ''} *
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
                          {choice.label}{choice.price_delta !== '0.00' ? ` (+${choice.price_delta} kr)` : ''}
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
                        {extra.name} ({extra.price} kr)
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
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  />
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
                        <option value={ticketType.id}>{ticketType.name} — {ticketType.price} kr</option>
                      {/each}
                    </select>
                  </div>
                {/if}

                {#each applicablePersonExtras(true).filter((extra) => extra.required) as extra (extra.id)}
                  {@const state = extraState(child.extraSelections, extra)}
                  <div class="md:col-span-2">
                    <div class="block text-xs text-neutral-600 mb-1">
                      {extra.name} {extra.price !== '0.00' ? `(${extra.price} kr)` : ''} *
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
                            {choice.label}{choice.price_delta !== '0.00' ? ` (+${choice.price_delta} kr)` : ''}
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
                          {extra.name} ({extra.price} kr)
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
            {extra.name} {extra.price !== '0.00' ? `(${extra.price} kr)` : ''} *
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
                  {choice.label}{choice.price_delta !== '0.00' ? ` (+${choice.price_delta} kr)` : ''}
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
                  {extra.name} ({extra.price} kr)
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

      {#if eventInfo.ticket_types.length > 0}
        <div class="mb-4 text-right text-sm font-semibold text-neutral-700" data-testid="register-running-total">
          {$t('register.totalLabel')}: {runningTotal.toFixed(2)} kr
        </div>
      {/if}

      <div class="flex items-center justify-end gap-3">
        <button
          type="submit"
          disabled={submitting || isPreview}
          title={isPreview ? $t('register.previewSubmitDisabled') : undefined}
          class="px-4 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors disabled:opacity-50"
          data-testid="register-submit-button"
        >
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
