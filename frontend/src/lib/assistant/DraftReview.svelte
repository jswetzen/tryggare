<script lang="ts">
  import { t } from 'svelte-i18n';
  import { assistantApi } from '$lib/api/assistantService';
  import type { ApiError } from '$lib/api/client';
  import Badge from '$lib/components/ui/Badge.svelte';
  import type { AssistantIssue, DraftPayload } from './types';
  import { summariseDiff } from './helpers';

  let {
    eventId,
    version,
    draftUnusable = false,
    pageStale = false,
    running = false,
    reload
  }: {
    eventId: string;
    // The store's draft counter: a change means "ask the server again".
    version: number;
    draftUnusable?: boolean;
    pageStale?: boolean;
    // A new run makes "saved" yesterday's news.
    running?: boolean;
    // Re-reads the page's spec after the draft is applied or discarded.
    reload: () => Promise<void> | void;
  } = $props();

  const MAX_LINES = 5;
  const MAX_ISSUES = 4;

  let draft = $state<DraftPayload | null>(null);
  let busy = $state<'apply' | 'discard' | null>(null);
  let applied = $state(false);
  let note = $state<'draftChanged' | null>(null);
  let failure = $state<{ key: string; issues: string[] } | null>(null);
  // Newest request wins; a slow answer for an older version is dropped.
  let seq = 0;

  const issuesOf = (err: unknown): AssistantIssue[] => {
    const errors = ((err as ApiError)?.details as { errors?: unknown } | undefined)?.errors;
    return Array.isArray(errors) ? (errors as AssistantIssue[]) : [];
  };

  async function load() {
    const mine = ++seq;
    try {
      const next = await assistantApi.getDraft(eventId);
      if (mine !== seq) return;
      draft = next;
      applied = false;
    } catch (err) {
      if (mine !== seq) return;
      draft = null;
      if ((err as ApiError)?.status !== 404) failure = { key: 'assistant.review.loadFailed', issues: [] };
    }
  }

  $effect(() => {
    if (running) applied = false;
  });

  $effect(() => {
    version;
    void load();
  });

  async function apply() {
    if (!draft || busy) return;
    const shown = draft;
    busy = 'apply';
    failure = null;
    note = null;
    try {
      await assistantApi.applySpec(eventId, shown.spec);
    } catch (err) {
      failure = {
        key: 'assistant.review.applyFailed',
        issues: issuesOf(err)
          .map((i) => i.message)
          .filter(Boolean)
          .slice(0, MAX_ISSUES)
      };
      busy = null;
      return;
    }
    // The setup is saved. Discarding names the draft that was reviewed, so a
    // newer one proposed meanwhile survives (409 draft_changed).
    try {
      await assistantApi.discardDraft(eventId, shown.version, shown.token);
      draft = null;
      applied = true;
    } catch (err) {
      if (issuesOf(err).some((i) => i.code === 'draft_changed')) {
        note = 'draftChanged';
        await load();
      } else {
        draft = null;
        applied = true;
      }
    }
    busy = null;
    await reload();
  }

  async function discard() {
    if (!draft || busy) return;
    const shown = draft;
    busy = 'discard';
    failure = null;
    note = null;
    try {
      await assistantApi.discardDraft(eventId, shown.version, shown.token);
      draft = null;
      applied = false;
    } catch (err) {
      if (issuesOf(err).some((i) => i.code === 'draft_changed')) {
        note = 'draftChanged';
        await load();
      } else if ((err as ApiError)?.status === 404) {
        draft = null;
      } else {
        failure = { key: 'assistant.review.discardFailed', issues: [] };
      }
    }
    busy = null;
    await reload();
  }

  // "200.00" reads as noise next to whole-krona prices.
  const money = (v: string) => v.replace(/\.00$/, '');
  const lines = $derived(draft ? summariseDiff(draft.diff) : []);
  const stale = $derived(!!draft && (draft.stale || pageStale));
</script>

{#if draft || applied || failure || note}
  <section class="review" aria-labelledby="assistant-review-title" data-testid="assistant-review">
    {#if applied && !draft}
      <p class="applied" role="status" data-testid="assistant-applied">
        <span aria-hidden="true">✓</span>
        {$t('assistant.review.applied')}
      </p>
    {/if}

    {#if note}
      <p class="alert">{$t(`assistant.review.${note}`)}</p>
    {/if}

    {#if draft}
      <header class="head">
        <h3 id="assistant-review-title" class="title">{$t('assistant.review.title')}</h3>
        <Badge color="primary" variant="soft" size="sm">{$t('assistant.preview.draft')}</Badge>
      </header>

      {#if lines.length === 0}
        <p class="muted">{$t('assistant.review.none')}</p>
      {:else}
        <ul class="changes">
          {#each lines.slice(0, MAX_LINES) as line}
            <li>
              <span class="kind">{$t(`assistant.review.kind.${line.kind}`)}</span>
              <span class="name">{line.name}</span>
              <span class="what">{$t(`assistant.review.change.${line.change}`)}{line.price ? `, ${money(line.price)} kr` : ''}</span>
              {#if line.fields.length}
                <span class="fields">{$t('assistant.review.changedFields', { values: { fields: line.fields.join(', ') } })}</span>
              {/if}
            </li>
          {/each}
          {#if lines.length > MAX_LINES}
            <li class="muted">{$t('assistant.review.more', { values: { count: lines.length - MAX_LINES } })}</li>
          {/if}
        </ul>
      {/if}

      {#if draft.warnings.length}
        <details class="warnings">
          <summary>{$t('assistant.review.warnings')} ({draft.warnings.length})</summary>
          <ul>
            {#each draft.warnings.slice(0, MAX_ISSUES) as w}
              <li>{w.message}</li>
            {/each}
          </ul>
        </details>
      {/if}

      {#if draftUnusable}
        <p class="alert" data-testid="assistant-review-unusable">{$t('assistant.preview.draftUnusable')}</p>
      {:else if stale}
        <p class="alert" data-testid="assistant-review-stale">{$t('assistant.review.stale')}</p>
      {/if}
    {/if}

    {#if failure}
      <div class="alert error" data-testid="assistant-review-error">
        <p>{$t(failure.key)}</p>
        {#if failure.issues.length}
          <ul>
            {#each failure.issues as issue}<li>{issue}</li>{/each}
          </ul>
        {/if}
      </div>
    {/if}

    {#if draft}
      <div class="actions">
        <button type="button" class="apply" disabled={!!busy || draftUnusable} onclick={apply}>
          {busy === 'apply' ? $t('assistant.review.applying') : $t('assistant.review.apply')}
        </button>
        <button type="button" class="discard" disabled={!!busy} onclick={discard}>
          {busy === 'discard' ? $t('assistant.review.discarding') : $t('assistant.review.discard')}
        </button>
      </div>
    {/if}
  </section>
{/if}

<style>
  .review {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--ink-line);
    background: var(--surface-2);
    max-height: 45%;
    overflow-y: auto;
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }
  .title {
    margin: 0;
    font-size: var(--type-body-sm);
    font-weight: var(--weight-bold);
    color: var(--ink);
  }
  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .changes {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    font-size: var(--type-body-sm);
  }
  .changes li {
    display: flex;
    flex-wrap: wrap;
    gap: 0 var(--space-2);
    align-items: baseline;
  }
  .kind {
    font-size: var(--type-caption);
    color: var(--ink-soft);
  }
  .name {
    font-weight: var(--weight-semi);
    overflow-wrap: anywhere;
  }
  .what,
  .fields {
    color: var(--ink-soft);
  }
  .muted {
    margin: 0;
    font-size: var(--type-caption);
    color: var(--ink-soft);
  }
  .warnings {
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--ink-line);
    font-size: var(--type-caption);
  }
  .warnings summary {
    cursor: pointer;
    font-weight: var(--weight-bold);
  }
  .warnings ul {
    margin-top: var(--space-1);
  }
  .warnings li {
    color: var(--ink-soft);
    overflow-wrap: anywhere;
  }
  .alert {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--ink-line-2);
    font-size: var(--type-caption);
    color: var(--ink);
  }
  .alert.error {
    background: var(--danger-tint);
    border-color: transparent;
    color: var(--danger);
  }
  .alert p {
    margin: 0;
  }
  .alert ul {
    margin-top: var(--space-1);
    padding-left: var(--space-4);
    list-style: disc;
  }
  .applied {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius);
    background: var(--brand-accent-tint);
    color: var(--brand-accent-mid);
    font-size: var(--type-body-sm);
    font-weight: var(--weight-semi);
  }
  .actions {
    display: flex;
    gap: var(--space-2);
  }
  .apply,
  .discard {
    min-height: 40px;
    padding: 0 var(--space-4);
    border-radius: var(--radius);
    font-size: var(--type-body-sm);
    font-weight: var(--weight-semi);
    transition: background var(--motion-base);
  }
  .apply {
    flex: 1;
    background: var(--brand-primary);
    color: var(--surface);
  }
  .apply:hover:not(:disabled) {
    background: var(--brand-primary-mid);
  }
  .discard {
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--ink-line-2);
  }
  .discard:hover:not(:disabled) {
    background: var(--ink-line);
  }
  .apply:disabled,
  .discard:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .apply:focus-visible,
  .discard:focus-visible {
    outline: 2px solid var(--brand-primary);
    outline-offset: 2px;
  }
</style>
