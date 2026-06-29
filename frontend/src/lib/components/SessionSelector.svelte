<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { Session } from '$lib/api/types';

  interface SessionSelectorProps {
    show?: boolean;
    sessions: Session[];
    currentSession: Session | null;
    onSelect: (session: Session) => void;
    onClose: () => void;
  }

  let {
    show = false,
    sessions,
    currentSession,
    onSelect,
    onClose
  }: SessionSelectorProps = $props();

  function handleSelect(session: Session) {
    onSelect(session);
  }

  function handleClose() {
    onClose();
  }

  function handleBackdropClick() {
    handleClose();
  }

  function handleModalClick(e: MouseEvent) {
    e.stopPropagation();
  }

  function formatTime(isoString: string): string {
    return new Date(isoString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }
</script>

{#if show}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    onclick={handleBackdropClick}
    role="presentation"
  >
    <div
      class="bg-white rounded-card shadow-xl max-w-md w-full mx-4"
      onclick={handleModalClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-selector-title"
    >
      <div class="p-6">
        <h2 id="session-selector-title" class="text-xl font-bold text-neutral-900 mb-4">
          {$_('session.changeSession')}
        </h2>
        <div class="space-y-2">
          {#each sessions as session (session.id)}
            <button
              onclick={() => handleSelect(session)}
              class="w-full text-left p-4 rounded-button border-2 transition-colors
                {currentSession?.id === session.id
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-neutral-200 hover:border-primary-300 hover:bg-neutral-50'}"
              aria-pressed={currentSession?.id === session.id}
            >
              <div class="font-semibold text-neutral-900">{session.name}</div>
              <div class="text-sm text-neutral-600">{session.event_name}</div>
              <div class="text-sm text-neutral-500">
                {formatTime(session.start_time)} - {session.end_time ? formatTime(session.end_time) : 'Open'}
              </div>
            </button>
          {/each}
        </div>
        <div class="mt-4 flex justify-end">
          <button
            onclick={handleClose}
            class="px-4 py-2 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-button transition-colors"
          >
            {$_('common.cancel')}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
