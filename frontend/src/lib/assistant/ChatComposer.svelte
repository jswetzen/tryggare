<script lang="ts">
  import { t } from 'svelte-i18n';
  import Icon from '$lib/components/ui/Icon.svelte';

  let {
    value = $bindable(''),
    running = false,
    disabled = false,
    sendDisabled = false,
    onsend,
    oncancel,
    inputEl = $bindable<HTMLTextAreaElement | null>(null)
  }: {
    value?: string;
    running?: boolean;
    disabled?: boolean;
    // Typing stays possible (offline); only sending is held back.
    sendDisabled?: boolean;
    onsend: (text: string) => void;
    oncancel: () => void;
    inputEl?: HTMLTextAreaElement | null;
  } = $props();

  const canSend = $derived(!disabled && !sendDisabled && !running && value.trim().length > 0);

  function submit() {
    if (!canSend) return;
    onsend(value.trim());
  }

  function onkeydown(e: KeyboardEvent) {
    // Enter sends, Shift+Enter adds a line; an IME composition keeps its Enter.
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  // Grows with the text up to a cap, then scrolls.
  function grow() {
    if (!inputEl) return;
    inputEl.style.height = 'auto';
    inputEl.style.height = `${Math.min(inputEl.scrollHeight, 140)}px`;
  }
  $effect(() => {
    value;
    grow();
  });
</script>

<form
  class="composer"
  onsubmit={(e) => {
    e.preventDefault();
    submit();
  }}
>
  <label class="sr-only" for="assistant-input">{$t('assistant.input.label')}</label>
  <textarea
    id="assistant-input"
    bind:this={inputEl}
    bind:value
    {onkeydown}
    rows="1"
    maxlength="4000"
    {disabled}
    placeholder={$t('assistant.input.placeholder')}
    aria-describedby="assistant-input-hint"
  ></textarea>
  {#if running}
    <button type="button" class="action stop" onclick={oncancel}>
      <span aria-hidden="true" class="stop-mark"></span>
      {$t('assistant.cancel')}
    </button>
  {:else}
    <button type="submit" class="action send" disabled={!canSend} aria-label={$t('assistant.send')}>
      <Icon name="send" size="sm" class="rotate-90" />
    </button>
  {/if}
</form>
<p id="assistant-input-hint" class="hint">{$t('assistant.input.hint')}</p>

<style>
  .composer {
    display: flex;
    align-items: flex-end;
    gap: var(--space-2);
  }
  textarea {
    flex: 1;
    min-width: 0;
    min-height: 44px;
    max-height: 140px;
    resize: none;
    padding: 10px var(--space-3);
    border: 1px solid var(--ink-line-2);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    font-size: var(--type-body-sm);
    line-height: 1.5;
  }
  textarea::placeholder {
    color: var(--ink-faint);
  }
  textarea:focus-visible {
    outline: 2px solid var(--brand-primary);
    outline-offset: 0;
    border-color: var(--brand-primary);
  }
  textarea:disabled {
    background: var(--surface-2);
  }
  .action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    flex-shrink: 0;
    min-width: 44px;
    min-height: 44px;
    padding: 0 var(--space-3);
    border-radius: var(--radius);
    font-weight: var(--weight-semi);
    font-size: var(--type-body-sm);
    transition: background var(--motion-base), opacity var(--motion-base);
  }
  .send {
    background: var(--brand-primary);
    color: var(--surface);
  }
  .send:hover:not(:disabled) {
    background: var(--brand-primary-mid);
  }
  .send:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .stop {
    background: var(--surface-2);
    color: var(--ink);
    border: 1px solid var(--ink-line-2);
  }
  .stop:hover {
    background: var(--ink-line);
  }
  .stop-mark {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    background: currentColor;
  }
  .action:focus-visible {
    outline: 2px solid var(--brand-primary);
    outline-offset: 2px;
  }
  .hint {
    margin: var(--space-1) 0 0;
    font-size: var(--type-caption);
    color: var(--ink-soft);
  }
</style>
