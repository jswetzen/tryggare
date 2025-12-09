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

  let {
    onAdd,
    onClose
  }: {
    onAdd: (data: {
      familyName: string;
      childrenNames: string[];
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

  let familyName = $state('');
  let childrenNames = $state(['']);
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
    childrenNames = [...childrenNames, ''];
  }

  function handleRemoveChild(index: number) {
    childrenNames = childrenNames.filter((_, i) => i !== index);
  }

  function handleChildNameChange(index: number, value: string) {
    const newNames = [...childrenNames];
    newNames[index] = value;
    childrenNames = newNames;
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

    // Filter out empty child names and validate
    const validChildren = childrenNames
      .map((name) => name.trim())
      .filter((name) => name.length > 0);

    if (validChildren.length === 0) {
      error = $_('checkin.atLeastOneChildRequired');
      return;
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

    if (validParents.length === 0) {
      error = 'At least one parent is required';
      return;
    }

    // Submit
    onAdd({
      familyName: familyName.trim(),
      childrenNames: validChildren,
      ticketType,
      parents: validParents,
    });
  }
</script>

<svelte:window on:keydown={handleKeyDown} />

<div
  class="bg-white border border-slate-300 rounded-lg p-4 mb-4 shadow-sm"
  data-testid="add-family-panel"
>
  <form on:submit={handleSubmit}>
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-bold text-slate-900">{$_('checkin.addFamilyTitle')}</h2>
      <button
        type="button"
        on:click={onClose}
        aria-label={$_('common.close')}
        class="text-slate-400 hover:text-slate-600 transition-colors text-xl"
        data-testid="add-family-close-button"
      >
        ✕
      </button>
    </div>

    <!-- Error message -->
    {#if error}
      <div class="mb-4 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
        {error}
      </div>
    {/if}

    <!-- Family Name -->
    <div class="mb-4">
      <label
        for="family-name"
        class="block text-sm font-semibold text-slate-700 mb-1"
      >
        {$_('checkin.familyName')}:
      </label>
      <input
        bind:this={familyNameInput}
        id="family-name"
        type="text"
        bind:value={familyName}
        placeholder={$_('checkin.familyNamePlaceholder')}
        class="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        data-testid="add-family-name-input"
      />
    </div>

    <!-- Parents -->
    <div class="mb-4">
      <div class="block text-sm font-semibold text-slate-700 mb-2">
        Parents:
      </div>
      <div class="space-y-3">
        {#each parents as parent, index (index)}
          <div class="border border-slate-200 rounded p-3 bg-slate-50">
            <div class="grid grid-cols-2 gap-2 mb-2">
              <div>
                <label for={`parent-name-${index}`} class="block text-xs text-slate-600 mb-1">
                  Name *
                </label>
                <input
                  id={`parent-name-${index}`}
                  type="text"
                  value={parent.name}
                  on:input={(e) => handleParentChange(index, 'name', e.currentTarget.value)}
                  placeholder="Parent name"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label for={`parent-relationship-${index}`} class="block text-xs text-slate-600 mb-1">
                  Relationship
                </label>
                <select
                  id={`parent-relationship-${index}`}
                  value={parent.relationship_type}
                  on:change={(e) => handleParentChange(index, 'relationship_type', e.currentTarget.value)}
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="MOM">Mom</option>
                  <option value="DAD">Dad</option>
                  <option value="GUARDIAN">Guardian</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label for={`parent-phone-${index}`} class="block text-xs text-slate-600 mb-1">
                  Phone
                </label>
                <input
                  id={`parent-phone-${index}`}
                  type="tel"
                  value={parent.phone}
                  on:input={(e) => handleParentChange(index, 'phone', e.currentTarget.value)}
                  placeholder="555-1234"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label for={`parent-email-${index}`} class="block text-xs text-slate-600 mb-1">
                  Email
                </label>
                <input
                  id={`parent-email-${index}`}
                  type="email"
                  value={parent.email}
                  on:input={(e) => handleParentChange(index, 'email', e.currentTarget.value)}
                  placeholder="email@example.com"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            {#if index > 0}
              <button
                type="button"
                on:click={() => handleRemoveParent(index)}
                class="mt-2 text-red-600 hover:text-red-700 text-xs font-medium"
              >
                Remove Parent
              </button>
            {/if}
          </div>
        {/each}
      </div>
      <button
        type="button"
        on:click={handleAddParent}
        class="mt-2 text-blue-600 hover:text-blue-700 text-sm font-semibold"
      >
        + Add Another Parent
      </button>
    </div>

    <!-- Ticket Type Selector -->
    <div class="mb-4">
      <label
        for="ticket-type"
        class="block text-sm font-semibold text-slate-700 mb-1"
      >
        {$_('checkin.ticketType')}:
      </label>
      <select
        id="ticket-type"
        bind:value={ticketType}
        class="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="none">{$_('checkin.ticketNone')}</option>
        <option value="session">{$_('checkin.ticketSession')}</option>
        <option value="event">{$_('checkin.ticketEvent')}</option>
      </select>
    </div>

    <!-- Children -->
    <div class="mb-4">
      <div class="block text-sm font-semibold text-slate-700 mb-2">
        {$_('checkin.children')}:
      </div>
      <div class="space-y-2">
        {#each childrenNames as name, index (index)}
          <div class="flex items-center gap-2">
            <input
              type="text"
              bind:value={childrenNames[index]}
              placeholder={$_('checkin.childNamePlaceholder')}
              class="flex-1 px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {#if index > 0}
              <button
                type="button"
                on:click={() => handleRemoveChild(index)}
                aria-label={$_('checkin.removeChildLabel')}
                class="text-red-600 hover:text-red-700 text-sm font-medium px-2 py-1"
              >
                {$_('common.remove')}
              </button>
            {/if}
          </div>
        {/each}
      </div>
      <button
        type="button"
        on:click={handleAddChild}
        class="mt-2 text-blue-600 hover:text-blue-700 text-sm font-semibold"
      >
        {$_('checkin.addAnotherChild')}
      </button>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3">
      <button
        type="button"
        on:click={onClose}
        class="px-4 py-2 bg-slate-200 text-slate-700 font-semibold rounded-lg hover:bg-slate-300 transition-colors"
        data-testid="add-family-cancel-button"
      >
        {$_('common.cancel')}
      </button>
      <button
        type="submit"
        class="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
        data-testid="add-family-submit-button"
      >
        {$_('checkin.addNewFamily')}
      </button>
    </div>
  </form>
</div>
