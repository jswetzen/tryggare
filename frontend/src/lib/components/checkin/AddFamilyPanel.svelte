<script lang="ts">
  /**
   * AddFamilyPanel Component
   *
   * Expands between session bar and search to add families with children.
   * Allows setting a default ticket type for all children in the family.
   */
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TicketType } from '$lib/checkin/types';
  import { isValidPhone } from '$lib/utils/phone';

  type HealthInfoStatus = 'none' | 'consented' | 'declined';
  type HealthConsentStatus = 'not_applicable' | 'granted' | 'declined';

  interface Child {
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
  }

  interface OutgoingChild {
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
    health_consent_status: HealthConsentStatus;
  }

  let {
    onAdd,
    onClose
  }: {
    onAdd: (data: {
      familyName: string;
      children: OutgoingChild[];
      ticketType: TicketType;
      parents: Array<{
        name: string;
        phone: string;
        email: string;
        relationship_type: string;
      }>;
    }) => void;
    onClose: () => void;
  } = $props();

  function emptyChild(): Child {
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

  let familyName = $state('');
  let children = $state<Child[]>([emptyChild()]);
  let ticketType = $state<TicketType>('none');
  let parents = $state([
    {
      name: '',
      phone: '',
      email: '',
      relationship_type: 'OTHER',
    },
  ]);
  let error = $state('');
  let familyNameInput = $state<HTMLInputElement>();

  // Focus family name input on mount
  onMount(() => {
    familyNameInput?.focus();
  });

  // Handle Escape key to close
  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onClose();
    }
  }

  function handleAddChild() {
    children = [...children, emptyChild()];
  }

  function handleRemoveChild(index: number) {
    children = children.filter((_, i) => i !== index);
  }

  function handleHealthInfoStatusChange(index: number, status: HealthInfoStatus) {
    const newChildren = [...children];
    newChildren[index] = { ...newChildren[index], healthInfoStatus: status };
    if (status !== 'consented') {
      // Declining or "none" both mean no health text is stored; clear
      // whatever was typed so a status flip can't leave stale text behind.
      newChildren[index].allergies = '';
      newChildren[index].notes = '';
      newChildren[index].consentNoticeShared = false;
    }
    children = newChildren;
  }

  function handleAddParent() {
    parents = [
      ...parents,
      {
        name: '',
        phone: '',
        email: '',
        relationship_type: 'OTHER',
      },
    ];
  }

  function handleRemoveParent(index: number) {
    parents = parents.filter((_, i) => i !== index);
  }

  function handleParentChange(
    index: number,
    field: 'name' | 'phone' | 'email' | 'relationship_type',
    value: string
  ) {
    const newParents = [...parents];
    newParents[index][field] = value;
    parents = newParents;
  }

  function handleSubmit(e: Event) {
    e.preventDefault();
    error = '';

    // Validate family name
    if (!familyName.trim()) {
      error = $_('checkin.familyNameRequired');
      return;
    }

    // A family is a household of attendees — all-children, all-parents, or
    // mixed are all valid, it just can't be empty (checked below, once we
    // know how many parents survived the empty-row filter).
    for (const child of children) {
      if (!child.first_name.trim() || !child.last_name.trim() || !child.birthdate.trim()) {
        error = $_('checkin.allChildrenRequired');
        return;
      }
      if (child.healthInfoStatus === 'consented' && !child.consentNoticeShared) {
        error = $_('checkin.healthConsentRequired');
        return;
      }
    }

    // Filter out parents with empty names and validate
    const validParents = parents
      .filter((parent) => parent.name.trim().length > 0)
      .map((parent) => ({
        name: parent.name.trim(),
        phone: parent.phone.trim(),
        email: parent.email.trim(),
        relationship_type: parent.relationship_type,
      }));

    if (children.length === 0 && validParents.length === 0) {
      error = $_('checkin.atLeastOneMemberRequired');
      return;
    }

    // Validate any provided phone numbers
    for (const parent of validParents) {
      if (!isValidPhone(parent.phone)) {
        error = $_('checkin.invalidPhone');
        return;
      }
    }

    // Submit
    const statusMap: Record<HealthInfoStatus, HealthConsentStatus> = {
      none: 'not_applicable',
      consented: 'granted',
      declined: 'declined',
    };
    const outgoingChildren: OutgoingChild[] = children.map((child) => ({
      first_name: child.first_name,
      last_name: child.last_name,
      birthdate: child.birthdate,
      allergies: child.healthInfoStatus === 'consented' ? child.allergies : '',
      notes: child.healthInfoStatus === 'consented' ? child.notes : '',
      health_consent_status: statusMap[child.healthInfoStatus],
    }));

    onAdd({
      familyName: familyName.trim(),
      children: outgoingChildren,
      ticketType,
      parents: validParents,
    });
  }
</script>

<svelte:window on:keydown={handleKeyDown} />

<div
  class="bg-white border border-neutral-300 rounded-card p-4 mb-4 shadow-sm"
  data-testid="add-family-panel"
>
  <form on:submit={handleSubmit}>
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-bold text-neutral-900">{$_('checkin.addFamilyTitle')}</h2>
      <button
        type="button"
        on:click={onClose}
        aria-label={$_('common.close')}
        class="text-neutral-400 hover:text-neutral-600 transition-colors text-xl"
        data-testid="add-family-close-button"
      >
        ✕
      </button>
    </div>

    <!-- Error message -->
    {#if error}
      <div class="mb-4 p-2 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
        {error}
      </div>
    {/if}

    <!-- Family Name -->
    <div class="mb-4">
      <label
        for="family-name"
        class="block text-sm font-semibold text-neutral-700 mb-1"
      >
        {$_('checkin.familyName')}:
      </label>
      <input
        bind:this={familyNameInput}
        id="family-name"
        type="text"
        bind:value={familyName}
        placeholder={$_('checkin.familyNamePlaceholder')}
        class="w-full px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
        data-testid="add-family-name-input"
      />
    </div>

    <!-- Parents -->
    <div class="mb-4">
      <div class="block text-sm font-semibold text-neutral-700 mb-2">
        {$_('checkin.parentInfo')}:
      </div>
      <div class="space-y-3">
        {#each parents as parent, index (index)}
          <div class="border border-neutral-200 rounded p-3 bg-neutral-50">
            <div class="grid grid-cols-2 gap-2 mb-2">
              <div>
                <label for={`parent-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.parentName')} *
                </label>
                <input
                  id={`parent-name-${index}`}
                  type="text"
                  value={parent.name}
                  on:input={(e) => handleParentChange(index, 'name', e.currentTarget.value)}
                  placeholder={$_('checkin.parentNamePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label for={`parent-relationship-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.relationshipType')}
                </label>
                <select
                  id={`parent-relationship-${index}`}
                  value={parent.relationship_type}
                  on:change={(e) => handleParentChange(index, 'relationship_type', e.currentTarget.value)}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="MOM">{$_('checkin.relationshipMom')}</option>
                  <option value="DAD">{$_('checkin.relationshipDad')}</option>
                  <option value="GUARDIAN">{$_('checkin.relationshipGuardian')}</option>
                  <option value="OTHER">{$_('checkin.relationshipOther')}</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label for={`parent-phone-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.parentPhone')}
                </label>
                <input
                  id={`parent-phone-${index}`}
                  type="tel"
                  value={parent.phone}
                  on:input={(e) => handleParentChange(index, 'phone', e.currentTarget.value)}
                  placeholder={$_('checkin.parentPhonePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label for={`parent-email-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.parentEmail')}
                </label>
                <input
                  id={`parent-email-${index}`}
                  type="email"
                  value={parent.email}
                  on:input={(e) => handleParentChange(index, 'email', e.currentTarget.value)}
                  placeholder={$_('checkin.parentEmailPlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <button
              type="button"
              on:click={() => handleRemoveParent(index)}
              class="mt-2 text-danger-600 hover:text-danger-700 text-xs font-medium"
            >
              {$_('checkin.removeParent')}
            </button>
          </div>
        {/each}
      </div>
      <button
        type="button"
        on:click={handleAddParent}
        class="mt-2 text-primary-600 hover:text-primary-700 text-sm font-semibold"
      >
        + {$_('checkin.addParent')}
      </button>
    </div>

    <!-- Ticket Type Selector -->
    <div class="mb-4">
      <label
        for="ticket-type"
        class="block text-sm font-semibold text-neutral-700 mb-1"
      >
        {$_('checkin.ticketType')}:
      </label>
      <select
        id="ticket-type"
        bind:value={ticketType}
        class="w-full px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="none">{$_('checkin.ticketNone')}</option>
        <option value="session">{$_('checkin.ticketSession')}</option>
        <option value="event">{$_('checkin.ticketEvent')}</option>
      </select>
    </div>

    <!-- Children -->
    <div class="mb-4">
      <div class="block text-sm font-semibold text-neutral-700 mb-2">
        {$_('checkin.children')}:
      </div>
      <div class="space-y-3">
        {#each children as child, index (index)}
          <div class="border border-neutral-200 rounded p-3 bg-neutral-50">
            <div class="flex justify-between items-center mb-2">
              <span class="text-sm font-semibold text-neutral-700">{$_('checkin.childNumber', { values: { number: index + 1 } })}</span>
              <button
                type="button"
                on:click={() => handleRemoveChild(index)}
                class="text-danger-600 hover:text-danger-700 text-xs font-medium"
              >
                {$_('checkin.removeChild')}
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                <label for={`child-first-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.childFirstName')} <span class="text-danger-600">*</span>
                </label>
                <input
                  id={`child-first-name-${index}`}
                  type="text"
                  bind:value={child.first_name}
                  placeholder={$_('checkin.childFirstNamePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>

              <div>
                <label for={`child-last-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.childLastName')} <span class="text-danger-600">*</span>
                </label>
                <input
                  id={`child-last-name-${index}`}
                  type="text"
                  bind:value={child.last_name}
                  placeholder={$_('checkin.childLastNamePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>

              <div>
                <label for={`child-birthdate-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.childBirthdate')} <span class="text-danger-600">*</span>
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
                <div class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.healthInfoQuestion')}
                </div>
                <div class="flex flex-col gap-1">
                  <label class="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name={`health-info-status-${index}`}
                      checked={child.healthInfoStatus === 'none'}
                      on:change={() => handleHealthInfoStatusChange(index, 'none')}
                    />
                    {$_('checkin.healthInfoNone')}
                  </label>
                  <label class="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name={`health-info-status-${index}`}
                      checked={child.healthInfoStatus === 'consented'}
                      on:change={() => handleHealthInfoStatusChange(index, 'consented')}
                    />
                    {$_('checkin.healthInfoConsent')}
                  </label>
                  <label class="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name={`health-info-status-${index}`}
                      checked={child.healthInfoStatus === 'declined'}
                      on:change={() => handleHealthInfoStatusChange(index, 'declined')}
                    />
                    {$_('checkin.healthInfoDecline')}
                  </label>
                </div>
              </div>

              {#if child.healthInfoStatus === 'consented'}
                <div class="md:col-span-2 border border-primary-200 bg-primary-50 rounded p-3 space-y-3">
                  <p class="text-xs text-neutral-700">{$_('checkin.healthConsentNotice')}</p>
                  <label class="flex items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      class="mt-0.5"
                      bind:checked={child.consentNoticeShared}
                      data-testid={`child-consent-attest-${index}`}
                    />
                    {$_('checkin.healthConsentAttest')}
                  </label>

                  <div>
                    <label for={`child-allergies-${index}`} class="block text-xs text-neutral-600 mb-1">
                      {$_('checkin.childAllergies')} <span class="text-neutral-400 text-xs">({$_('checkin.optional')})</span>
                    </label>
                    <input
                      id={`child-allergies-${index}`}
                      type="text"
                      bind:value={child.allergies}
                      placeholder={$_('checkin.childAllergiesPlaceholder')}
                      class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>

                  <div>
                    <label for={`child-notes-${index}`} class="block text-xs text-neutral-600 mb-1">
                      {$_('checkin.childNotes')} <span class="text-neutral-400 text-xs">({$_('checkin.optional')})</span>
                    </label>
                    <textarea
                      id={`child-notes-${index}`}
                      bind:value={child.notes}
                      placeholder={$_('checkin.childNotesPlaceholder')}
                      rows="2"
                      class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                    ></textarea>
                  </div>
                </div>
              {:else if child.healthInfoStatus === 'declined'}
                <div class="md:col-span-2">
                  <p class="text-xs text-neutral-500 italic">{$_('checkin.healthInfoDeclinedNote')}</p>
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
      <button
        type="button"
        on:click={handleAddChild}
        class="mt-2 text-primary-600 hover:text-primary-700 text-sm font-semibold"
      >
        + {$_('checkin.addAnotherChild')}
      </button>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3">
      <button
        type="button"
        on:click={onClose}
        class="px-4 py-2 bg-neutral-200 text-neutral-700 font-semibold rounded-button hover:bg-neutral-300 transition-colors"
        data-testid="add-family-cancel-button"
      >
        {$_('common.cancel')}
      </button>
      <button
        type="submit"
        class="px-4 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors"
        data-testid="add-family-submit-button"
      >
        {$_('checkin.addNewFamily')}
      </button>
    </div>
  </form>
</div>
