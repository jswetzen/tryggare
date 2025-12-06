<script lang="ts">
  /**
   * AddFamilyPanel Component
   *
   * Expands between session bar and search to add families with children.
   * Allows setting a default ticket type for all children in the family.
   */
  import { onMount } from 'svelte';
  import type { TicketType } from '$lib/checkin/types';

  let {
    onAdd,
    onClose
  }: {
    onAdd: (data: {
      familyName: string;
      childrenNames: string[];
      ticketType: TicketType;
    }) => void;
    onClose: () => void;
  } = $props();

  let familyName = $state('');
  let childrenNames = $state(['']);
  let ticketType = $state<TicketType>('none');
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

  function handleSubmit(e: Event) {
    e.preventDefault();
    error = '';

    // Validate family name
    if (!familyName.trim()) {
      error = 'Family name is required';
      return;
    }

    // Filter out empty child names and validate
    const validChildren = childrenNames
      .map((name) => name.trim())
      .filter((name) => name.length > 0);

    if (validChildren.length === 0) {
      error = 'At least one child name is required';
      return;
    }

    // Submit
    onAdd({
      familyName: familyName.trim(),
      childrenNames: validChildren,
      ticketType,
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
      <h2 class="text-lg font-bold text-slate-900">Add New Family</h2>
      <button
        type="button"
        on:click={onClose}
        aria-label="Close"
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
        Family Name:
      </label>
      <input
        bind:this={familyNameInput}
        id="family-name"
        type="text"
        bind:value={familyName}
        placeholder="Garcia, Smith, etc."
        class="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        data-testid="add-family-name-input"
      />
    </div>

    <!-- Ticket Type Selector -->
    <div class="mb-4">
      <label
        for="ticket-type"
        class="block text-sm font-semibold text-slate-700 mb-1"
      >
        Ticket:
      </label>
      <select
        id="ticket-type"
        bind:value={ticketType}
        class="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="none">No Ticket</option>
        <option value="session">Session Only</option>
        <option value="event">Full Event Pass</option>
      </select>
    </div>

    <!-- Children -->
    <div class="mb-4">
      <div class="block text-sm font-semibold text-slate-700 mb-2">
        Children:
      </div>
      <div class="space-y-2">
        {#each childrenNames as name, index (index)}
          <div class="flex items-center gap-2">
            <input
              type="text"
              bind:value={childrenNames[index]}
              placeholder={`Child ${index + 1} name`}
              class="flex-1 px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {#if index > 0}
              <button
                type="button"
                on:click={() => handleRemoveChild(index)}
                aria-label="Remove child"
                class="text-red-600 hover:text-red-700 text-sm font-medium px-2 py-1"
              >
                Remove
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
        + Add Child
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
        Cancel
      </button>
      <button
        type="submit"
        class="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
        data-testid="add-family-submit-button"
      >
        Add Family
      </button>
    </div>
  </form>
</div>
