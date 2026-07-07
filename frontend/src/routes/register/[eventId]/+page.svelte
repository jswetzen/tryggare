<script lang="ts">
  /**
   * Public self-serve event registration form.
   *
   * Parallel to the existing public /qr/[token] route: unauthenticated,
   * no persistent guardian account. On submit, the backend materializes
   * Family/Parent/Child rows immediately (status=pending_verification) and
   * emails a one-time verification link — see /register/verify/[token].
   */
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { registrationApi } from '$lib/api/registrationService';
  import type { RegistrationEventInfo } from '$lib/api/types';
  import ConsentCapture, { type HealthInfoStatus } from '$lib/components/checkin/ConsentCapture.svelte';
  import { isValidPhone } from '$lib/utils/phone';

  type HealthConsentStatus = 'not_applicable' | 'granted' | 'declined';

  interface ParentRow {
    first_name: string;
    phone: string;
    email: string;
    relationship_type: string;
  }

  interface ChildRow {
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
  }

  const eventId = $derived($page.params.eventId ?? '');

  function emptyParent(): ParentRow {
    return { first_name: '', phone: '', email: '', relationship_type: 'OTHER' };
  }

  function emptyChild(): ChildRow {
    return {
      first_name: '',
      last_name: '',
      birthdate: '',
      allergies: '',
      notes: '',
      healthInfoStatus: 'none',
      consentNoticeShared: false
    };
  }

  let eventInfo = $state<RegistrationEventInfo | null>(null);
  let loadingEvent = $state(true);
  let eventNotFound = $state(false);

  let familyName = $state('');
  let contactEmail = $state('');
  let parents = $state<ParentRow[]>([emptyParent()]);
  let children = $state<ChildRow[]>([emptyChild()]);
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

    const validParents = parents
      .filter((p) => p.first_name.trim().length > 0)
      .map((p) => ({
        first_name: p.first_name.trim(),
        phone: p.phone.trim(),
        email: p.email.trim(),
        relationship_type: p.relationship_type
      }));

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
        parents: validParents,
        children: children.map((child) => ({
          first_name: child.first_name.trim(),
          last_name: child.last_name.trim(),
          birthdate: child.birthdate,
          allergies: child.healthInfoStatus === 'consented' ? child.allergies : '',
          notes: child.healthInfoStatus === 'consented' ? child.notes : '',
          health_consent_status: statusMap[child.healthInfoStatus]
        })),
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
    <form
      on:submit={handleSubmit}
      class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm"
      data-testid="register-form"
    >
      <h1 class="text-2xl font-bold text-neutral-900 mb-1">
        {$t('register.heading', { values: { event: eventInfo.name } })}
      </h1>
      <p class="text-sm text-neutral-600 mb-1">{$t('register.introText')}</p>
      {#if eventInfo.is_paid && eventInfo.price}
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
                    class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  />
                </div>

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

      <div class="flex items-center justify-end gap-3">
        <button
          type="submit"
          disabled={submitting}
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
