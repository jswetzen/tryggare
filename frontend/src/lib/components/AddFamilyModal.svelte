<script lang="ts">
  import { t } from 'svelte-i18n';
  import { familyApi } from '$lib/api/services';
  import { isValidPhone } from '$lib/utils/phone';

  interface Props {
    show: boolean;
    onClose: () => void;
    onSuccess: () => void;
  }

  let { show = $bindable(), onClose, onSuccess }: Props = $props();

  interface Parent {
    name: string;
    phone: string;
    email: string;
    relationship_type: string;
  }

  interface Child {
    first_name: string;
    last_name: string;
    birthdate: string;
    allergies: string;
    notes: string;
  }

  let parents = $state<Parent[]>([
    { name: '', phone: '', email: '', relationship_type: 'Mom' }
  ]);

  let children = $state<Child[]>([
    { first_name: '', last_name: '', birthdate: '', allergies: '', notes: '' }
  ]);

  let submitting = $state(false);
  let error = $state<string | null>(null);

  function addParent() {
    parents = [...parents, { name: '', phone: '', email: '', relationship_type: 'Mom' }];
  }

  function removeParent(index: number) {
    if (parents.length > 1) {
      parents = parents.filter((_, i) => i !== index);
    }
  }

  function addChild() {
    children = [...children, { first_name: '', last_name: '', birthdate: '', allergies: '', notes: '' }];
  }

  function removeChild(index: number) {
    if (children.length > 1) {
      children = children.filter((_, i) => i !== index);
    }
  }

  function validateForm(): boolean {
    // Check at least one parent
    if (parents.length === 0 || !parents.some(p => p.name.trim())) {
      error = $t('checkin.atLeastOneParent');
      return false;
    }

    // Check all parents have names and valid (optional) phone numbers
    for (const parent of parents) {
      if (!parent.name.trim()) {
        error = $t('checkin.validationError');
        return false;
      }
      if (!isValidPhone(parent.phone)) {
        error = $t('checkin.invalidPhone');
        return false;
      }
    }

    // Check at least one child
    if (children.length === 0) {
      error = $t('checkin.atLeastOneChild');
      return false;
    }

    // Check all children have required fields
    for (const child of children) {
      if (!child.first_name.trim() || !child.last_name.trim() || !child.birthdate.trim()) {
        error = $t('checkin.validationError');
        return false;
      }
    }

    return true;
  }

  async function handleSubmit() {
    error = null;

    if (!validateForm()) {
      return;
    }

    submitting = true;

    try {
      // Prepare data for API
      const parentsData = parents.map(p => ({
        name: p.name.trim(),
        phone: p.phone.trim() || undefined,
        email: p.email.trim() || undefined,
        relationship_type: p.relationship_type
      }));

      const childrenData = children.map(c => ({
        first_name: c.first_name.trim(),
        last_name: c.last_name.trim(),
        birthdate: c.birthdate.trim(),
        allergies: c.allergies.trim() || undefined,
        notes: c.notes.trim() || undefined
      }));

      await familyApi.create({
        parents: parentsData,
        children: childrenData
      });

      // Reset form
      parents = [{ name: '', phone: '', email: '', relationship_type: 'Mom' }];
      children = [{ first_name: '', last_name: '', birthdate: '', allergies: '', notes: '' }];

      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to create family:', err);
      error = $t('checkin.createError');
    } finally {
      submitting = false;
    }
  }

  function handleCancel() {
    // Reset form
    parents = [{ name: '', phone: '', email: '', relationship_type: 'Mom' }];
    children = [{ first_name: '', last_name: '', birthdate: '', allergies: '', notes: '' }];
    error = null;
    onClose();
  }
</script>

{#if show}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 overflow-y-auto">
    <div class="bg-white rounded-card p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
      <h2 class="text-2xl font-bold mb-6">{$t('checkin.addFamilyTitle')}</h2>

      {#if error}
        <div class="bg-danger-50 border border-danger-200 rounded-button p-4 mb-4">
          <div class="text-danger-800 font-semibold">{error}</div>
        </div>
      {/if}

      <!-- Parents Section -->
      <div class="mb-8">
        <h3 class="text-xl font-semibold mb-4">{$t('checkin.parentInfo')}</h3>

        {#each parents as parent, index}
          <div class="border border-neutral-300 rounded-button p-4 mb-4">
            <div class="flex justify-between items-center mb-3">
              <span class="font-semibold text-neutral-700">Parent {index + 1}</span>
              {#if parents.length > 1}
                <button
                  type="button"
                  class="text-danger-600 hover:text-danger-700 text-sm"
                  onclick={() => removeParent(index)}
                >
                  {$t('checkin.removeParent')}
                </button>
              {/if}
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.parentName')} <span class="text-danger-600">*</span>
                </label>
                <input
                  type="text"
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder={$t('checkin.parentNamePlaceholder')}
                  bind:value={parent.name}
                  required
                />
              </div>

              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.relationshipType')} <span class="text-danger-600">*</span>
                </label>
                <select
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  bind:value={parent.relationship_type}
                >
                  <option value="Mom">{$t('checkin.relationshipMom')}</option>
                  <option value="Dad">{$t('checkin.relationshipDad')}</option>
                  <option value="Other">{$t('checkin.relationshipOther')}</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.parentPhone')}
                </label>
                <input
                  type="tel"
                  inputmode="tel"
                  class="w-full px-4 py-2 border rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500 {isValidPhone(
                    parent.phone
                  )
                    ? 'border-neutral-300'
                    : 'border-danger-400 focus:ring-danger-500'}"
                  placeholder={$t('checkin.parentPhonePlaceholder')}
                  bind:value={parent.phone}
                  aria-invalid={!isValidPhone(parent.phone)}
                />
                {#if !isValidPhone(parent.phone)}
                  <p class="mt-1 text-xs text-danger-600">{$t('checkin.invalidPhone')}</p>
                {/if}
              </div>

              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.parentEmail')}
                </label>
                <input
                  type="email"
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder={$t('checkin.parentEmailPlaceholder')}
                  bind:value={parent.email}
                />
              </div>
            </div>
          </div>
        {/each}

        <button
          type="button"
          class="bg-primary-100 hover:bg-primary-200 text-primary-700 font-semibold px-4 py-2 rounded-button"
          onclick={addParent}
        >
          + {$t('checkin.addParent')}
        </button>
      </div>

      <!-- Children Section -->
      <div class="mb-8">
        <h3 class="text-xl font-semibold mb-4">{$t('checkin.childInfo')}</h3>

        {#each children as child, index}
          <div class="border border-neutral-300 rounded-button p-4 mb-4">
            <div class="flex justify-between items-center mb-3">
              <span class="font-semibold text-neutral-700">Child {index + 1}</span>
              {#if children.length > 1}
                <button
                  type="button"
                  class="text-danger-600 hover:text-danger-700 text-sm"
                  onclick={() => removeChild(index)}
                >
                  {$t('checkin.removeChild')}
                </button>
              {/if}
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.childFirstName')} <span class="text-danger-600">*</span>
                </label>
                <input
                  type="text"
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder={$t('checkin.childFirstNamePlaceholder')}
                  bind:value={child.first_name}
                  required
                />
              </div>

              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.childLastName')} <span class="text-danger-600">*</span>
                </label>
                <input
                  type="text"
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder={$t('checkin.childLastNamePlaceholder')}
                  bind:value={child.last_name}
                  required
                />
              </div>

              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.childBirthdate')} <span class="text-danger-600">*</span>
                </label>
                <input
                  type="date"
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  bind:value={child.birthdate}
                  required
                />
              </div>

              <div>
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.childAllergies')}
                </label>
                <input
                  type="text"
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder={$t('checkin.childAllergiesPlaceholder')}
                  bind:value={child.allergies}
                />
              </div>

              <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-neutral-700 mb-1">
                  {$t('checkin.childNotes')}
                </label>
                <textarea
                  class="w-full px-4 py-2 border border-neutral-300 rounded-input focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows="2"
                  placeholder={$t('checkin.childNotesPlaceholder')}
                  bind:value={child.notes}
                ></textarea>
              </div>
            </div>
          </div>
        {/each}

        <button
          type="button"
          class="bg-success-100 hover:bg-success-200 text-success-700 font-semibold px-4 py-2 rounded-button"
          onclick={addChild}
        >
          + {$t('checkin.addChild')}
        </button>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-3 justify-end">
        <button
          type="button"
          class="bg-neutral-200 hover:bg-neutral-300 text-neutral-800 font-semibold px-6 py-2 rounded-button"
          onclick={handleCancel}
          disabled={submitting}
        >
          {$t('common.cancel')}
        </button>
        <button
          type="button"
          class="bg-primary-600 hover:bg-primary-700 text-white font-semibold px-6 py-2 rounded-button"
          onclick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? $t('checkin.creating') : $t('checkin.createFamily')}
        </button>
      </div>
    </div>
  </div>
{/if}
