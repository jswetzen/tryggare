<script lang="ts">
  /**
   * SessionIndicator Component
   *
   * Displays current event and session information with buttons to:
   * - Change the current session
   * - Add a new family
   */

  export let eventName: string;
  export let sessionName: string;
  export let sessionTime: string;
  export let onChangeSession: () => void;
  export let onAddFamily: () => void;
</script>

<div
  class="bg-slate-50 border border-slate-300 rounded px-3 py-2 mb-4 flex flex-wrap justify-between items-center gap-2 text-sm"
  data-testid="session-indicator"
>
  <div class="text-slate-600">
    <span class="font-semibold text-blue-900">Event:</span> {eventName} •
    <span class="font-semibold text-blue-900 ml-1">Session:</span> {sessionName} ({sessionTime})
  </div>
  <div class="flex gap-2">
    <button
      on:click={onChangeSession}
      class="px-3 py-1.5 text-blue-600 font-semibold hover:underline"
      data-testid="change-session-button"
    >
      Change Session
    </button>
    <button
      on:click={onAddFamily}
      class="px-3 py-1.5 bg-blue-600 text-white font-semibold rounded hover:bg-blue-700 transition-colors"
      data-testid="add-family-button"
    >
      + Add Family
    </button>
  </div>
</div>
