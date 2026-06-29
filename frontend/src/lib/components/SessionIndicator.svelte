<script lang="ts">
  /**
   * SessionIndicator Component
   *
   * Displays current event and session information with optional buttons to:
   * - Change the current session (only shown when onChangeSession provided AND showChangeSession is true)
   * - Add a new family (only shown when onAddFamily provided AND showAddFamily is true)
   */

  import { _ } from 'svelte-i18n';

  let {
    eventName,
    sessionName,
    sessionTime,
    onChangeSession = undefined,
    onAddFamily = undefined,
    showAddFamily = true,
    showChangeSession = true,
  }: {
    eventName: string;
    sessionName: string;
    sessionTime: string;
    onChangeSession?: (() => void) | undefined;
    onAddFamily?: (() => void) | undefined;
    showAddFamily?: boolean;
    showChangeSession?: boolean;
  } = $props();
</script>

<div
  class="bg-neutral-50 border border-neutral-300 rounded px-3 py-2 mb-4 flex flex-wrap justify-between items-center gap-2 text-sm"
  data-testid="session-indicator"
>
  <div class="text-neutral-600">
    <span class="font-semibold text-primary-900">{$_('session.event')}</span> {eventName} •
    <span class="font-semibold text-primary-900 ml-1">{$_('session.session')}</span> {sessionName} ({sessionTime})
  </div>
  <div class="flex gap-2">
    {#if showChangeSession && onChangeSession}
      <button
        on:click={onChangeSession}
        class="px-3 py-1.5 text-primary-600 font-semibold hover:underline"
        data-testid="change-session-button"
      >
        {$_('session.changeSession')}
      </button>
    {/if}

    {#if showAddFamily && onAddFamily}
      <button
        on:click={onAddFamily}
        class="px-3 py-1.5 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors"
        data-testid="add-family-button"
      >
        {$_('checkin.addNewFamily')}
      </button>
    {/if}
  </div>
</div>
