<script lang="ts">
  import { t } from 'svelte-i18n';
  import { stripMarkdown } from './helpers';

  let { role, text }: { role: 'user' | 'assistant'; text: string } = $props();

  // Local models answer in Markdown; the chat shows plain text. Only paired
  // marks are dropped, so names like `__init__` or a lone `*` survive.
  const plain = $derived(role === 'assistant' ? stripMarkdown(text) : text);
</script>

<div class="row" data-role={role}>
  <p class="bubble">
    <span class="sr-only">{role === 'user' ? $t('assistant.you') : $t('assistant.assistant')}: </span>{plain}
  </p>
</div>

<style>
  .row {
    display: flex;
  }
  .row[data-role='user'] {
    justify-content: flex-end;
  }
  .bubble {
    max-width: 88%;
    margin: 0;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-md);
    font-size: var(--type-body-sm);
    line-height: 1.5;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    color: var(--ink);
  }
  /* Alignment plus a neutral tint tell the two voices apart; no avatars. */
  [data-role='user'] .bubble {
    background: var(--surface-2);
    border-bottom-right-radius: var(--radius-sm);
  }
  [data-role='assistant'] .bubble {
    background: var(--surface);
    border: 1px solid var(--ink-line);
    border-bottom-left-radius: var(--radius-sm);
  }
</style>
