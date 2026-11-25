<script lang="ts">
  import { t } from 'svelte-i18n';
  import Icon from '$lib/components/ui/Icon.svelte';

  let {
    onaccept,
    busy = false,
    failed = false,
    acceptEl = $bindable<HTMLButtonElement | null>(null)
  }: {
    onaccept: () => void;
    busy?: boolean;
    failed?: boolean;
    acceptEl?: HTMLButtonElement | null;
  } = $props();
</script>

<section class="notice" aria-labelledby="assistant-notice-title" data-testid="assistant-notice">
  <h3 id="assistant-notice-title" class="title">
    <Icon name="info" size="sm" />
    {$t('assistant.notice.title')}
  </h3>
  <p class="body">{$t('assistant.notice.body')}</p>
  {#if failed}
    <p class="failed">{$t('assistant.notice.failed')}</p>
  {/if}
  <!-- Plain button: Button.svelte cannot hand back its element for focus. -->
  <button
    bind:this={acceptEl}
    type="button"
    class="accept"
    disabled={busy}
    onclick={onaccept}
  >
    {$t('assistant.notice.accept')}
  </button>
</section>

<style>
  .notice {
    padding: var(--space-4);
    border-radius: var(--radius-md);
    background: var(--brand-primary-tint);
    color: var(--ink);
  }
  .title {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin: 0 0 var(--space-2);
    font-size: var(--type-body-sm);
    font-weight: var(--weight-bold);
    color: var(--brand-primary-mid);
  }
  .body {
    margin: 0 0 var(--space-3);
    font-size: var(--type-body-sm);
    line-height: 1.5;
  }
  .failed {
    margin: 0 0 var(--space-3);
    font-size: var(--type-caption);
    color: var(--danger);
  }
  .accept {
    min-height: 44px;
    padding: 0 var(--space-5);
    border-radius: var(--radius);
    background: var(--brand-primary);
    color: var(--surface);
    font-weight: var(--weight-semi);
    font-size: var(--type-body-sm);
    transition: background var(--motion-base);
  }
  .accept:hover:not(:disabled) {
    background: var(--brand-primary-mid);
  }
  .accept:focus-visible {
    outline: 2px solid var(--brand-primary);
    outline-offset: 2px;
  }
  .accept:disabled {
    opacity: 0.6;
  }
</style>
