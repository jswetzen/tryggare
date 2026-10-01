<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Badge from '$lib/components/ui/Badge.svelte';

  // A narrow local shape, not the full `$lib/api/types` or `$lib/checkin/types`
  // Session — this component only ever reads these fields, and the two
  // callers (checkin/+page.svelte, checkout/+page.svelte) pass structurally
  // different Session types that both happen to be supersets of this one.
  interface Session {
    id: string;
    name: string;
    event_name: string;
    start_time: string;
    end_time?: string;
    /** The ticket rule in force for this session (own rule, else the event default). */
    effective_ticket_rule?: 'open' | 'children' | 'all';
    /** Drop-off sessions: no adult is checked in, guardians included. */
    adults_not_checked_in?: boolean;
  }

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

  // One neutral pill per fact a volunteer needs before picking a desk: who has to hold a ticket,
  // and whether adults are checked in at all. Neutral on purpose: the choice is not a verdict.
  // A missing rule (an older server) shows no ticket pill rather than guessing.
  const RULE_KEYS = {
    open: 'session.ruleOpen',
    children: 'session.ruleChildren',
    all: 'session.ruleAll'
  } as const;

  function formatTime(isoString: string): string {
    return new Date(isoString).toLocaleTimeString('en-US', {
      timeZone: 'Europe/Stockholm',
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
              {#if session.effective_ticket_rule || session.adults_not_checked_in}
                <div class="flex flex-wrap gap-1.5 mt-2" data-testid={`session-rules-${session.id}`}>
                  {#if session.effective_ticket_rule}
                    <Badge color="secondary" variant="soft" size="sm">
                      {$_(RULE_KEYS[session.effective_ticket_rule])}
                    </Badge>
                  {/if}
                  {#if session.adults_not_checked_in}
                    <Badge color="secondary" variant="soft" size="sm">
                      {$_('session.adultsNotCheckedIn')}
                    </Badge>
                  {/if}
                </div>
              {/if}
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
