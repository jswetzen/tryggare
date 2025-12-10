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

  interface Child {
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
  }

  let {
    onAdd,
    onClose
  }: {
    onAdd: (data: {
      familyName: string;
      children: Child[];
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
  let children = $state<Child[]>([
    { first_name: '', last_name: '', birthdate: '', allergies: '', notes: '' }
  ]);
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
    children = [...children, { first_name: '', last_name: '', birthdate: '', allergies: '', notes: '' }];
  }

  function handleRemoveChild(index: number) {
    if (children.length > 1) {
      children = children.filter((_, i) => i !== index);
    }
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

    // Validate children - check required fields
    if (children.length === 0) {
      error = $_('checkin.atLeastOneChildRequired');
      return;
    }

    for (const child of children) {
      if (!child.first_name.trim() || !child.last_name.trim() || !child.birthdate.trim()) {
        error = 'All children must have first name, last name, and birthdate';
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

    if (validParents.length === 0) {
      error = 'At least one parent is required';
      return;
    }

    // Submit
    onAdd({
      familyName: familyName.trim(),
      children: children,
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
      <div class="space-y-3">
        {#each children as child, index (index)}
          <div class="border border-slate-200 rounded p-3 bg-slate-50">
            <div class="flex justify-between items-center mb-2">
              <span class="text-sm font-semibold text-slate-700">Child {index + 1}</span>
              {#if children.length > 1}
                <button
                  type="button"
                  on:click={() => handleRemoveChild(index)}
                  class="text-red-600 hover:text-red-700 text-xs font-medium"
                >
                  Remove Child
                </button>
              {/if}
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                <label for={`child-first-name-${index}`} class="block text-xs text-slate-600 mb-1">
                  First Name <span class="text-red-600">*</span>
                </label>
                <input
                  id={`child-first-name-${index}`}
                  type="text"
                  bind:value={child.first_name}
                  placeholder="First name"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label for={`child-last-name-${index}`} class="block text-xs text-slate-600 mb-1">
                  Last Name <span class="text-red-600">*</span>
                </label>
                <input
                  id={`child-last-name-${index}`}
                  type="text"
                  bind:value={child.last_name}
                  placeholder="Last name"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label for={`child-birthdate-${index}`} class="block text-xs text-slate-600 mb-1">
                  Birthdate <span class="text-red-600">*</span>
                </label>
                <input
                  id={`child-birthdate-${index}`}
                  type="date"
                  bind:value={child.birthdate}
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label for={`child-allergies-${index}`} class="block text-xs text-slate-600 mb-1">
                  Allergies <span class="text-slate-400 text-xs">(optional)</span>
                </label>
                <input
                  id={`child-allergies-${index}`}
                  type="text"
                  bind:value={child.allergies}
                  placeholder="Any allergies"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div class="md:col-span-2">
                <label for={`child-notes-${index}`} class="block text-xs text-slate-600 mb-1">
                  Notes <span class="text-slate-400 text-xs">(optional)</span>
                </label>
                <textarea
                  id={`child-notes-${index}`}
                  bind:value={child.notes}
                  placeholder="Any additional notes"
                  rows="2"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                ></textarea>
              </div>
            </div>
          </div>
        {/each}
      </div>
      <button
        type="button"
        on:click={handleAddChild}
        class="mt-2 text-blue-600 hover:text-blue-700 text-sm font-semibold"
      >
        + {$_('checkin.addAnotherChild')}
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
