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
   * are on one form. testIdPrefix defaults to 'child' for backwards
   * compatibility with existing tests; pass 'parent' when this instance is
   * capturing an adult's own data.
   *
   * attestLabelKey defaults to the staff-attesting-on-behalf-of-a-guardian
   * phrasing ("I've read this... to the guardian... they consent"). The
   * public self-serve form — where the guardian reads and ticks the box
   * themselves — must pass a first-person key instead; reusing the staff
   * wording there would read as grammatically backwards.
   *
   * questionKey/consentLabelKey/declineLabelKey/noticeKey/declinedNoteKey
   * all default to the original child-guardian wording — same reasoning as
   * attestLabelKey. An adult self-capturing their own data needs different
   * copy (there's no "guardian" in the sentence), so the registration page
   * passes register.adultHealthInfo* overrides for its parent rows.
   * noticeLinkHref/noticeLinkLabelKey optionally render a link under the
   * notice text (e.g. to the privacy policy) instead of restating the full
   * legal detail inline.
   *
   * canEdit=false switches the whole block to read-behind-reveal: no radios,
   * no inputs, just a flag saying safety info exists and a control that asks
   * for it. That is a Volontär's view of an existing family — they may not
   * change a record, but the person at the door is precisely the person who
   * needs to know about a peanut allergy, so this is reveal-with-audit rather
   * than hidden. Performing the reveal is the parent's job (one API call per
   * attendee, one audit row); this component owns only the control and the two
   * states either side of it.
   */
  import { _ } from 'svelte-i18n';
  import Icon from '$lib/components/ui/Icon.svelte';

  let {
    status = $bindable<HealthInfoStatus>('none'),
    allergies = $bindable(''),
    notes = $bindable(''),
    consentNoticeShared = $bindable(false),
    idPrefix,
    testIdPrefix = 'child',
    attestLabelKey = 'checkin.healthConsentAttest',
    questionKey = 'checkin.healthInfoQuestion',
    consentLabelKey = 'checkin.healthInfoConsent',
    declineLabelKey = 'checkin.healthInfoDecline',
    noticeKey = 'checkin.healthConsentNotice',
    declinedNoteKey = 'checkin.healthInfoDeclinedNote',
    noticeLinkHref = undefined,
    noticeLinkLabelKey = 'register.privacyLink',
    canEdit = true,
    hasSafetyInfo = false,
    revealed = false,
    revealing = false,
    revealError = '',
    onReveal = undefined
  }: {
    status?: HealthInfoStatus;
    allergies?: string;
    notes?: string;
    consentNoticeShared?: boolean;
    idPrefix: string;
    testIdPrefix?: string;
    attestLabelKey?: string;
    questionKey?: string;
    consentLabelKey?: string;
    declineLabelKey?: string;
    noticeKey?: string;
    declinedNoteKey?: string;
    noticeLinkHref?: string;
    noticeLinkLabelKey?: string;
    /** False = read-behind-reveal (see the component docstring). */
    canEdit?: boolean;
    /** The record carries allergy/medical text, whether or not it's shown. */
    hasSafetyInfo?: boolean;
    /** The text below has been through an audited reveal. */
    revealed?: boolean;
    revealing?: boolean;
    revealError?: string;
    onReveal?: () => void;
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

{#if !canEdit}
  <!-- Read-behind-reveal. Amber, not green: green is the trust/success/live
       signal in this design system, and a safety flag is neither. -->
  {#if hasSafetyInfo}
    <div class="border border-warning-600 bg-warning-50 rounded-card p-3 space-y-2">
      <div class="flex items-start gap-2">
        <span class="text-warning-800 flex-shrink-0 mt-0.5" aria-hidden="true">
          <Icon name="alert-triangle" size="sm" />
        </span>
        <div class="text-sm font-semibold text-warning-800">
          {$_('checkin.safetyInfoOnFile')}
        </div>
      </div>

      {#if revealed}
        <div class="space-y-2" data-testid={`${testIdPrefix}-safety-info-revealed-${idPrefix}`}>
          {#if allergies}
            <div class="bg-white border border-danger-200 rounded-card p-2">
              <div class="text-xs text-neutral-600">{$_('checkin.childAllergies')}</div>
              <div class="text-sm font-semibold text-danger-800">{allergies}</div>
            </div>
          {/if}
          {#if notes}
            <div class="bg-white border border-warning-600 rounded-card p-2">
              <div class="text-xs text-neutral-600">{$_('checkin.childNotes')}</div>
              <div class="text-sm font-semibold text-warning-800">{notes}</div>
            </div>
          {/if}
          <p class="text-xs text-neutral-600">{$_('checkin.safetyInfoRevealLogged')}</p>
        </div>
      {:else}
        <p class="text-xs text-neutral-700">{$_('checkin.safetyInfoRevealHint')}</p>
        <button
          type="button"
          on:click={() => onReveal?.()}
          disabled={revealing}
          class="inline-flex items-center gap-2 px-3 py-2 rounded-button bg-warning-600 text-white text-sm font-semibold hover:bg-warning-700 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-warning-600 focus:ring-offset-2"
          data-testid={`${testIdPrefix}-safety-info-reveal-${idPrefix}`}
        >
          <Icon name="eye" size="sm" />
          {revealing ? $_('common.loading') : $_('checkin.safetyInfoReveal')}
        </button>
      {/if}

      {#if revealError}
        <p class="text-xs font-semibold text-danger-800" role="alert">{revealError}</p>
      {/if}
    </div>
  {:else}
    <p class="text-xs text-neutral-500 italic">{$_('checkin.safetyInfoNone')}</p>
  {/if}
{:else}
<div>
  <div class="block text-xs text-neutral-600 mb-1">
    {$_(questionKey)}
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
      {$_(consentLabelKey)}
    </label>
    <label class="flex items-center gap-2 text-sm">
      <input
        type="radio"
        name={`health-info-status-${idPrefix}`}
        checked={status === 'declined'}
        on:change={() => handleStatusChange('declined')}
      />
      {$_(declineLabelKey)}
    </label>
  </div>
</div>

{#if status === 'consented'}
  <div class="border border-primary-200 bg-primary-50 rounded p-3 space-y-3">
    <p class="text-xs text-neutral-700">
      {$_(noticeKey)}
      {#if noticeLinkHref}
        <a href={noticeLinkHref} class="text-primary-600 hover:underline">{$_(noticeLinkLabelKey)}</a>
      {/if}
    </p>
    <label class="flex items-start gap-2 text-sm">
      <input
        type="checkbox"
        class="mt-0.5"
        bind:checked={consentNoticeShared}
        data-testid={`${testIdPrefix}-consent-attest-${idPrefix}`}
      />
      {$_(attestLabelKey)}
    </label>

    <div>
      <label for={`${testIdPrefix}-allergies-${idPrefix}`} class="block text-xs text-neutral-600 mb-1">
        {$_('checkin.childAllergies')} <span class="text-neutral-400 text-xs">({$_('checkin.optional')})</span>
      </label>
      <input
        id={`${testIdPrefix}-allergies-${idPrefix}`}
        type="text"
        bind:value={allergies}
        placeholder={$_('checkin.childAllergiesPlaceholder')}
        class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
      />
    </div>

    <div>
      <label for={`${testIdPrefix}-notes-${idPrefix}`} class="block text-xs text-neutral-600 mb-1">
        {$_('checkin.childNotes')} <span class="text-neutral-400 text-xs">({$_('checkin.optional')})</span>
      </label>
      <textarea
        id={`${testIdPrefix}-notes-${idPrefix}`}
        bind:value={notes}
        placeholder={$_('checkin.childNotesPlaceholder')}
        rows="2"
        class="w-full px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
      ></textarea>
    </div>
  </div>
{:else if status === 'declined'}
  <p class="text-xs text-neutral-500 italic">{$_(declinedNoteKey)}</p>
{/if}
{/if}
