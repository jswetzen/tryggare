<script lang="ts" module>
  export type HealthInfoStatus = 'none' | 'consented' | 'declined';
</script>

<script lang="ts">
  /**
   * ConsentCapture Component
   *
   * The tri-state health-info radio group + consent notice box + attestation
   * checkbox + allergies/notes fields, extracted from AddFamilyPanel so the
   * staff and public self-serve registration forms capture consent with
   * identical rigor (same clear-on-decline behavior, same notice text).
   *
   * idPrefix must be unique per instance on the page (e.g. the child's index)
   * so radio-group names and input ids don't collide when multiple children
   * are on one form.
   *
   * attestLabelKey defaults to the staff-attesting-on-behalf-of-a-guardian
   * phrasing ("I've read this... to the guardian... they consent"). The
   * public self-serve form — where the guardian reads and ticks the box
   * themselves — must pass a first-person key instead; reusing the staff
   * wording there would read as grammatically backwards.
   */
  import { _ } from 'svelte-i18n';

  let {
    status = $bindable<HealthInfoStatus>('none'),
    allergies = $bindable(''),
    notes = $bindable(''),
    consentNoticeShared = $bindable(false),
    idPrefix,
    attestLabelKey = 'checkin.healthConsentAttest'
  }: {
    status?: HealthInfoStatus;
    allergies?: string;
    notes?: string;
    consentNoticeShared?: boolean;
    idPrefix: string;
    attestLabelKey?: string;
  } = $props();

  function handleStatusChange(newStatus: HealthInfoStatus) {
    status = newStatus;
    if (newStatus !== 'consented') {
      // Declining or "none" both mean no health text is stored; clear
      // whatever was typed so a status flip can't leave stale text behind.
      allergies = '';
      notes = '';
      consentNoticeShared = false;
    }
  }
</script>

<div>
  <div class="block text-xs text-neutral-600 mb-1">
    {$_('checkin.healthInfoQuestion')}
  </div>
  <div class="flex flex-col gap-1">
    <label class="flex items-center gap-2 text-sm">
      <input
        type="radio"
        name={`health-info-status-${idPrefix}`}
        checked={status === 'none'}
        on:change={() => handleStatusChange('none')}
      />
      {$_('checkin.healthInfoNone')}
    </label>
    <label class="flex items-center gap-2 text-sm">
      <input
        type="radio"
        name={`health-info-status-${idPrefix}`}
        checked={status === 'consented'}
        on:change={() => handleStatusChange('consented')}
      />
      {$_('checkin.healthInfoConsent')}
    </label>
    <label class="flex items-center gap-2 text-sm">
      <input
        type="radio"
        name={`health-info-status-${idPrefix}`}
        checked={status === 'declined'}
        on:change={() => handleStatusChange('declined')}
      />
      {$_('checkin.healthInfoDecline')}
    </label>
  </div>
</div>

{#if status === 'consented'}
  <div class="border border-primary-200 bg-primary-50 rounded p-3 space-y-3">
    <p class="text-xs text-neutral-700">{$_('checkin.healthConsentNotice')}</p>
    <label class="flex items-start gap-2 text-sm">
      <input
        type="checkbox"
        class="mt-0.5"
        bind:checked={consentNoticeShared}
        data-testid={`child-consent-attest-${idPrefix}`}
      />
      {$_(attestLabelKey)}
    </label>

    <div>
      <label for={`child-allergies-${idPrefix}`} class="block text-xs text-neutral-600 mb-1">
        {$_('checkin.childAllergies')} <span class="text-neutral-400 text-xs">({$_('checkin.optional')})</span>
      </label>
      <input
        id={`child-allergies-${idPrefix}`}
        type="text"
        bind:value={allergies}
        placeholder={$_('checkin.childAllergiesPlaceholder')}
        class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
      />
    </div>

    <div>
      <label for={`child-notes-${idPrefix}`} class="block text-xs text-neutral-600 mb-1">
        {$_('checkin.childNotes')} <span class="text-neutral-400 text-xs">({$_('checkin.optional')})</span>
      </label>
      <textarea
        id={`child-notes-${idPrefix}`}
        bind:value={notes}
        placeholder={$_('checkin.childNotesPlaceholder')}
        rows="2"
        class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
      ></textarea>
    </div>
  </div>
{:else if status === 'declined'}
  <p class="text-xs text-neutral-500 italic">{$_('checkin.healthInfoDeclinedNote')}</p>
{/if}
