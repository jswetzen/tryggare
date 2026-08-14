<script lang="ts">
  /**
   * AddFamilyPanel Component
   *
   * Expands between session bar and search to add families with children.
   * Allows setting a default ticket type for all children in the family.
   *
   * In edit mode with canEditFamily=false — a Volontär looking at an existing
   * family — the panel is a read-only family detail view instead: no writable
   * fields, no save, and the allergy/emergency-medical text behind an explicit
   * reveal (see ConsentCapture). That mirrors the API, which hands a Volontär
   * `has_safety_info` but not the text, and refuses the PATCH this form would
   * otherwise submit. Offering an edit form that can only 403 would be the
   * worse failure: it teaches the door staff that the app is broken.
   */
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { Family, TicketType } from '$lib/checkin/types';
  import { isValidPhone } from '$lib/utils/phone';
  import ConsentCapture, { type HealthInfoStatus } from './ConsentCapture.svelte';

  type HealthConsentStatus = 'not_applicable' | 'granted' | 'declined';

  interface Child {
    id?: string;
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
    /** Text exists on the record, whether or not this viewer has seen it. */
    hasSafetyInfo: boolean;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
  }

  interface OutgoingChild {
    id?: string;
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
    health_consent_status: HealthConsentStatus;
  }

  interface Parent {
    id?: string;
    first_name: string;
    last_name: string;
    phone: string;
    email: string;
    relationship_type: string;
    allergies: string;
    notes: string;
    /** Text exists on the record, whether or not this viewer has seen it. */
    hasSafetyInfo: boolean;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
  }

  interface OutgoingParent {
    id?: string;
    first_name: string;
    last_name: string;
    phone: string;
    email: string;
    relationship_type: string;
    allergies: string;
    notes: string;
    health_consent_status: HealthConsentStatus;
  }

  let {
    family,
    onAdd,
    onSave,
    onClose,
    canEditFamily = true,
    onRevealSafetyInfo = undefined
  }: {
    /** Present = edit an existing family; absent = create a new one. */
    family?: Family | null;
    onAdd: (data: {
      familyName: string;
      children: OutgoingChild[];
      ticketType: TicketType;
      parents: OutgoingParent[];
    }) => void;
    onSave?: (data: {
      familyId: string;
      familyName: string;
      children: OutgoingChild[];
      ticketType: TicketType;
      parents: OutgoingParent[];
    }) => void;
    onClose: () => void;
    /** False = this viewer may not write families; edit mode becomes read-only. */
    canEditFamily?: boolean;
    /**
     * Perform one audited reveal for `attendeeId` (a child or a parent) and
     * resolve with the text. Owned by the page because it is an API call that
     * writes an audit row, not a piece of form state.
     */
    onRevealSafetyInfo?: (
      attendeeId: string
    ) => Promise<{ allergies: string; notes: string }>;
  } = $props();

  const isEditMode = !!family;
  /** Creating a family is unaffected: this is only ever the existing-record view. */
  const readOnly = isEditMode && !canEditFamily;

  function emptyChild(): Child {
    return {
      first_name: '',
      last_name: '',
      birthdate: '',
      allergies: '',
      notes: '',
      hasSafetyInfo: false,
      healthInfoStatus: 'none',
      consentNoticeShared: false
    };
  }

  function emptyParent(): Parent {
    return {
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      relationship_type: 'OTHER',
      allergies: '',
      notes: '',
      hasSafetyInfo: false,
      healthInfoStatus: 'none',
      consentNoticeShared: false
    };
  }

  // Reverse of the create-path statusMap below — an already-granted consent
  // pre-fills consentNoticeShared=true so editing an unrelated field doesn't
  // force re-attesting a notice that was already shown. withdrawn/
  // needs_reconfirmation aren't directly settable through this form's
  // three-state toggle, so they fall back to 'none' rather than crashing.
  function statusFromBackend(status: string | undefined): HealthInfoStatus {
    if (status === 'granted') return 'consented';
    if (status === 'declined') return 'declined';
    return 'none';
  }

  function childFromExisting(child: Family['children'][number]): Child {
    return {
      id: child.id,
      first_name: child.first_name,
      last_name: child.last_name,
      birthdate: child.birthdate ?? '',
      allergies: child.allergies ?? '',
      notes: child.notes ?? '',
      hasSafetyInfo: child.has_safety_info ?? Boolean(child.allergies || child.notes),
      healthInfoStatus: statusFromBackend(child.health_consent_status),
      consentNoticeShared: child.health_consent_status === 'granted'
    };
  }

  function parentFromExisting(parent: Family['parents'][number]): Parent {
    return {
      id: parent.id,
      first_name: parent.first_name,
      last_name: parent.last_name,
      phone: parent.phone ?? '',
      email: parent.email ?? '',
      relationship_type: parent.relationship_type,
      allergies: parent.allergies ?? '',
      notes: parent.notes ?? '',
      hasSafetyInfo: parent.has_safety_info ?? Boolean(parent.allergies || parent.notes),
      healthInfoStatus: statusFromBackend(parent.health_consent_status),
      consentNoticeShared: parent.health_consent_status === 'granted'
    };
  }

  let familyName = $state(family?.last_name ?? '');
  let children = $state<Child[]>(family ? family.children.map(childFromExisting) : [emptyChild()]);
  // Only ever assigns tickets to newly-added rows (see handleAddFamily/
  // handleEditFamily in +page.svelte) — never reflects or changes a
  // pre-existing member's ticket, so it has no sensible pre-fill from
  // `family` in edit mode (see the hint shown alongside it below).
  let ticketType = $state<TicketType>('none');
  let parents = $state<Parent[]>(family ? family.parents.map(parentFromExisting) : [emptyParent()]);
  let error = $state('');
  let familyNameInput = $state<HTMLInputElement>();

  // Reveal state, keyed by attendee id. Per-attendee rather than per-panel:
  // one reveal is one audit row about one person, and revealing a child's
  // allergy must not silently disclose their sibling's.
  let revealedIds = $state<Record<string, boolean>>({});
  let revealingIds = $state<Record<string, boolean>>({});
  let revealErrors = $state<Record<string, string>>({});

  async function revealSafetyInfo(kind: 'child' | 'parent', index: number) {
    const row = kind === 'child' ? children[index] : parents[index];
    const attendeeId = row.id;
    if (!attendeeId || !onRevealSafetyInfo) return;

    revealingIds = { ...revealingIds, [attendeeId]: true };
    revealErrors = { ...revealErrors, [attendeeId]: '' };
    try {
      const revealed = await onRevealSafetyInfo(attendeeId);
      if (kind === 'child') {
        children[index].allergies = revealed.allergies;
        children[index].notes = revealed.notes;
      } else {
        parents[index].allergies = revealed.allergies;
        parents[index].notes = revealed.notes;
      }
      revealedIds = { ...revealedIds, [attendeeId]: true };
    } catch (err) {
      console.error('Failed to reveal safety info:', err);
      revealErrors = {
        ...revealErrors,
        [attendeeId]: $_('checkin.safetyInfoRevealError')
      };
    } finally {
      revealingIds = { ...revealingIds, [attendeeId]: false };
    }
  }

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

  function handleAddParent() {
    parents = [...parents, emptyParent()];
  }

  function handleRemoveParent(index: number) {
    parents = parents.filter((_, i) => i !== index);
  }

  function handleParentChange(
    index: number,
    field: 'first_name' | 'last_name' | 'phone' | 'email' | 'relationship_type',
    value: string
  ) {
    const newParents = [...parents];
    newParents[index][field] = value;
    parents = newParents;
  }

  function handleSubmit(e: Event) {
    e.preventDefault();
    // The submit button isn't rendered in the read-only view, but a form can
    // still be submitted by pressing Enter in a field, and the API would answer
    // that with a 403 nobody asked for.
    if (readOnly) return;
    error = '';

    // Validate family name
    if (!familyName.trim()) {
      error = $_('checkin.familyNameRequired');
      return;
    }

    const statusMap: Record<HealthInfoStatus, HealthConsentStatus> = {
      none: 'not_applicable',
      consented: 'granted',
      declined: 'declined',
    };

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

    // Parents are optional rows (unlike children) — only the ones with a
    // name entered are validated/submitted; a still-empty row is silently
    // dropped, same as before this consent block existed.
    for (const parent of parents) {
      if (!parent.first_name.trim()) continue;
      if (parent.healthInfoStatus === 'consented' && !parent.consentNoticeShared) {
        error = $_('checkin.adultHealthConsentRequired');
        return;
      }
    }

    // Filter out parents with empty names and validate
    const validParents: OutgoingParent[] = parents
      .filter((parent) => parent.first_name.trim().length > 0)
      .map((parent) => ({
        id: parent.id,
        first_name: parent.first_name.trim(),
        last_name: parent.last_name.trim(),
        phone: parent.phone.trim(),
        email: parent.email.trim(),
        relationship_type: parent.relationship_type,
        allergies: parent.healthInfoStatus === 'consented' ? parent.allergies : '',
        notes: parent.healthInfoStatus === 'consented' ? parent.notes : '',
        health_consent_status: statusMap[parent.healthInfoStatus],
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
    const outgoingChildren: OutgoingChild[] = children.map((child) => ({
      id: child.id,
      first_name: child.first_name,
      last_name: child.last_name,
      birthdate: child.birthdate,
      allergies: child.healthInfoStatus === 'consented' ? child.allergies : '',
      notes: child.healthInfoStatus === 'consented' ? child.notes : '',
      health_consent_status: statusMap[child.healthInfoStatus],
    }));

    if (isEditMode && family && onSave) {
      onSave({
        familyId: family.id,
        familyName: familyName.trim(),
        children: outgoingChildren,
        ticketType,
        parents: validParents,
      });
      return;
    }

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
      <h2 class="text-lg font-bold text-neutral-900">
        {$_(
          readOnly
            ? 'checkin.familyDetailsTitle'
            : isEditMode
              ? 'checkin.editFamilyTitle'
              : 'checkin.addFamilyTitle'
        )}
      </h2>
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

    {#if readOnly}
      <p class="mb-4 text-sm text-neutral-600">{$_('checkin.familyDetailsReadOnly')}</p>
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
        disabled={readOnly}
        class="w-full px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
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
                <label for={`parent-first-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.parentFirstName')} *
                </label>
                <input
                  id={`parent-first-name-${index}`}
                  disabled={readOnly}
                  type="text"
                  value={parent.first_name}
                  on:input={(e) => handleParentChange(index, 'first_name', e.currentTarget.value)}
                  placeholder={$_('checkin.parentFirstNamePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
                />
              </div>
              <div>
                <label for={`parent-last-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.parentLastName')}
                </label>
                <input
                  id={`parent-last-name-${index}`}
                  disabled={readOnly}
                  type="text"
                  value={parent.last_name}
                  on:input={(e) => handleParentChange(index, 'last_name', e.currentTarget.value)}
                  placeholder={$_('checkin.parentLastNamePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
                />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2 mb-2">
              <div>
                <label for={`parent-relationship-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.relationshipType')}
                </label>
                <select
                  id={`parent-relationship-${index}`}
                  disabled={readOnly}
                  value={parent.relationship_type}
                  on:change={(e) => handleParentChange(index, 'relationship_type', e.currentTarget.value)}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
                >
                  <option value="MOM">{$_('checkin.relationshipMom')}</option>
                  <option value="DAD">{$_('checkin.relationshipDad')}</option>
                  <option value="GUARDIAN">{$_('checkin.relationshipGuardian')}</option>
                  <option value="OTHER">{$_('checkin.relationshipOther')}</option>
                </select>
              </div>
              <div>
                <label for={`parent-phone-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.parentPhone')}
                </label>
                <input
                  id={`parent-phone-${index}`}
                  disabled={readOnly}
                  type="tel"
                  value={parent.phone}
                  on:input={(e) => handleParentChange(index, 'phone', e.currentTarget.value)}
                  placeholder={$_('checkin.parentPhonePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
                />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label for={`parent-email-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.parentEmail')}
                </label>
                <input
                  id={`parent-email-${index}`}
                  disabled={readOnly}
                  type="email"
                  value={parent.email}
                  on:input={(e) => handleParentChange(index, 'email', e.currentTarget.value)}
                  placeholder={$_('checkin.parentEmailPlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
                />
              </div>
            </div>
            <div class="mt-2">
              <ConsentCapture
                bind:status={parent.healthInfoStatus}
                bind:allergies={parent.allergies}
                bind:notes={parent.notes}
                bind:consentNoticeShared={parent.consentNoticeShared}
                idPrefix={`parent-${index}`}
                testIdPrefix="parent"
                attestLabelKey="checkin.adultHealthConsentAttest"
                questionKey="checkin.adultHealthInfoQuestion"
                consentLabelKey="checkin.adultHealthInfoConsent"
                declineLabelKey="checkin.adultHealthInfoDecline"
                noticeKey="checkin.adultHealthConsentNotice"
                declinedNoteKey="checkin.adultHealthInfoDeclinedNote"
                canEdit={!readOnly}
                hasSafetyInfo={parent.hasSafetyInfo}
                revealed={Boolean(parent.id && revealedIds[parent.id])}
                revealing={Boolean(parent.id && revealingIds[parent.id])}
                revealError={(parent.id && revealErrors[parent.id]) || ''}
                onReveal={() => revealSafetyInfo('parent', index)}
              />
            </div>
            {#if !readOnly}
              <button
                type="button"
                on:click={() => handleRemoveParent(index)}
                class="mt-2 text-danger-600 hover:text-danger-700 text-xs font-medium"
              >
                {$_('checkin.removeParent')}
              </button>
            {/if}
          </div>
        {/each}
      </div>
      {#if !readOnly}
        <button
          type="button"
          on:click={handleAddParent}
          class="mt-2 text-primary-600 hover:text-primary-700 text-sm font-semibold"
        >
          + {$_('checkin.addParent')}
        </button>
      {/if}
    </div>

    <!-- Ticket Type Selector. Only ever applies to rows added in this panel,
         so it has nothing to say in the read-only view. -->
    {#if !readOnly}
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
      {#if isEditMode}
        <p class="text-xs text-neutral-500 mt-1">{$_('checkin.ticketTypeNewMembersHint')}</p>
      {/if}
    </div>
    {/if}

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
              {#if !readOnly}
                <button
                  type="button"
                  on:click={() => handleRemoveChild(index)}
                  class="text-danger-600 hover:text-danger-700 text-xs font-medium"
                >
                  {$_('checkin.removeChild')}
                </button>
              {/if}
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                <label for={`child-first-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.childFirstName')} <span class="text-danger-600">*</span>
                </label>
                <input
                  id={`child-first-name-${index}`}
                  disabled={readOnly}
                  type="text"
                  bind:value={child.first_name}
                  placeholder={$_('checkin.childFirstNamePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
                  required
                />
              </div>

              <div>
                <label for={`child-last-name-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.childLastName')} <span class="text-danger-600">*</span>
                </label>
                <input
                  id={`child-last-name-${index}`}
                  disabled={readOnly}
                  type="text"
                  bind:value={child.last_name}
                  placeholder={$_('checkin.childLastNamePlaceholder')}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
                  required
                />
              </div>

              <div>
                <label for={`child-birthdate-${index}`} class="block text-xs text-neutral-600 mb-1">
                  {$_('checkin.childBirthdate')} <span class="text-danger-600">*</span>
                </label>
                <input
                  id={`child-birthdate-${index}`}
                  disabled={readOnly}
                  type="date"
                  bind:value={child.birthdate}
                  class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-600"
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
                  canEdit={!readOnly}
                  hasSafetyInfo={child.hasSafetyInfo}
                  revealed={Boolean(child.id && revealedIds[child.id])}
                  revealing={Boolean(child.id && revealingIds[child.id])}
                  revealError={(child.id && revealErrors[child.id]) || ''}
                  onReveal={() => revealSafetyInfo('child', index)}
                />
              </div>
            </div>
          </div>
        {/each}
      </div>
      {#if !readOnly}
        <button
          type="button"
          on:click={handleAddChild}
          class="mt-2 text-primary-600 hover:text-primary-700 text-sm font-semibold"
        >
          + {$_('checkin.addAnotherChild')}
        </button>
      {/if}
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3">
      <button
        type="button"
        on:click={onClose}
        class="px-4 py-2 bg-neutral-200 text-neutral-700 font-semibold rounded-button hover:bg-neutral-300 transition-colors"
        data-testid="add-family-cancel-button"
      >
        {$_(readOnly ? 'common.close' : 'common.cancel')}
      </button>
      {#if !readOnly}
        <button
          type="submit"
          class="px-4 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors"
          data-testid="add-family-submit-button"
        >
          {$_(isEditMode ? 'checkin.saveFamilyChanges' : 'checkin.addNewFamily')}
        </button>
      {/if}
    </div>
  </form>
</div>
