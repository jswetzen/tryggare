<script lang="ts">
  /**
   * One feature request the assistant filed, waiting for the organizer. Nothing
   * is stored until Confirm is clicked (docs/roadmap/feature_requests.md, "How the
   * assistant files one"). Confirm, Edit and Discard are the only ways out.
   */
  import { tick } from 'svelte';
  import { t } from 'svelte-i18n';
  import { assistantApi } from '$lib/api/assistantService';
  import type { ApiError } from '$lib/api/client';
  import Badge from '$lib/components/ui/Badge.svelte';
  import {
    COSTS,
    FEATURE_LIMITS,
    checkForm,
    editsFrom,
    fieldIdOf,
    fieldOfPath,
    formFrom,
    issueList,
    type FeatureField,
    type FeatureForm,
    type FieldProblem
  } from './featureRequest';
  import type { AssistantIssue, FeatureRequestCard, FeatureRequestEdits } from './types';

  let {
    eventId,
    card,
    ondone,
    onremoved,
    ondiscarded
  }: {
    eventId: string;
    card: FeatureRequestCard;
    // The title is the one the server stored: an edited Confirm changes it.
    ondone: (id: string, outcome: 'confirmed' | 'duplicate', duplicateOf: string | null, title: string) => void;
    onremoved: (id: string) => void;
    // Only a discard the server accepted: onremoved also runs for a card already gone.
    ondiscarded?: (id: string) => void;
  } = $props();

  let editing = $state(false);
  let form = $state<FeatureForm>({ title: '', problem: '', desired: '', tried: [], used: '', cost: 'none' });
  let problems = $state<FieldProblem[]>([]);
  let busy = $state<'confirm' | 'discard' | null>(null);
  let failure = $state<'save' | 'discard' | null>(null);
  let issues = $state<AssistantIssue[]>([]);
  // Set by a Confirm that succeeded here: focus then moves to the receipt.
  let acted = $state(false);

  let editBtn = $state<HTMLButtonElement | null>(null);
  let confirmBtn = $state<HTMLButtonElement | null>(null);
  let errorEl = $state<HTMLElement | null>(null);
  let doneEl = $state<HTMLDivElement | null>(null);

  const settled = $derived(card.outcome ?? null);
  const hasWorkaround = $derived(card.workaround !== null && card.workaround !== undefined);
  // Without the GET's answer (tried is missing) an edit would show blank fields.
  const canEdit = $derived(!settled && card.tried !== undefined);
  const prefix = $derived(`fr-${card.id.replace(/[^A-Za-z0-9-]/g, '')}`);
  const costWord = (cost: string) => $t(`assistant.featureRequest.cost.${cost}`);

  $effect(() => {
    if (settled && acted) void tick().then(() => doneEl?.focus());
  });

  function problemFor(field: FeatureField): FieldProblem | undefined {
    return problems.find((p) => p.field === field);
  }
  // The error joins the hint, so focusing an invalid field reads why.
  const describedBy = (field: FeatureField): string =>
    problemFor(field)
      ? `${fieldIdOf(prefix, field)}-hint ${fieldIdOf(prefix, field)}-error`
      : `${fieldIdOf(prefix, field)}-hint`;
  function problemText(p: FieldProblem): string {
    return p.code === 'required'
      ? $t('assistant.featureRequest.error.required')
      : $t('assistant.featureRequest.error.tooLong', { values: { max: p.max } });
  }
  const issueLabel = (path: string): string => {
    switch (fieldOfPath(path)) {
      case 'title':
        return $t('assistant.featureRequest.field.title');
      case 'problem':
        return $t('assistant.featureRequest.field.problem');
      case 'desired':
        return $t('assistant.featureRequest.field.desired');
      case 'tried':
        return $t('assistant.featureRequest.field.tried');
      case 'used':
        return $t('assistant.featureRequest.field.used');
      default:
        return '';
    }
  };

  function startEdit() {
    form = formFrom(card);
    problems = [];
    issues = [];
    failure = null;
    editing = true;
    void tick().then(() => document.getElementById(fieldIdOf(prefix, 'title'))?.focus());
  }

  function cancelEdit() {
    editing = false;
    problems = [];
    issues = [];
    failure = null;
    void tick().then(() => editBtn?.focus());
  }

  function onKey(e: KeyboardEvent) {
    // Escape in a field cancels the edit; it must not also minimize the chat.
    if (e.key === 'Escape' && editing) {
      e.stopPropagation();
      cancelEdit();
    }
  }

  const issuesOf = (err: unknown): AssistantIssue[] =>
    issueList(((err as ApiError)?.details as { errors?: unknown } | undefined)?.errors);

  async function confirm() {
    if (busy || settled) return;
    let edits: FeatureRequestEdits | undefined;
    if (editing) {
      problems = checkForm(form, hasWorkaround);
      if (problems.length) {
        await tick();
        const first = problems[0].field;
        document.getElementById(fieldIdOf(prefix, first))?.focus();
        return;
      }
      edits = editsFrom(form, hasWorkaround);
    }
    busy = 'confirm';
    failure = null;
    issues = [];
    let refused = false;
    try {
      const done = await assistantApi.confirmFeatureRequest(eventId, card.id, edits);
      editing = false;
      acted = true;
      ondone(card.id, done.status, done.duplicate_of, edits?.title ?? card.title);
    } catch (err) {
      const status = (err as ApiError)?.status;
      const found = issuesOf(err);
      // Gone on the server (confirmed or discarded elsewhere): nothing to review here.
      if (status === 404 || found.some((i) => i.code === 'not_a_draft')) {
        onremoved(card.id);
        return;
      }
      if (status === 400) issues = found.slice(0, 6);
      failure = 'save';
      refused = true;
    } finally {
      busy = null;
    }
    // Disabling Confirm while busy dropped focus to the body; Escape needs focus inside the card.
    if (refused) void tick().then(focusAfterFailure);
  }

  // The field the server named if it is on screen, else the error box, else Confirm.
  function focusAfterFailure() {
    for (const issue of issues) {
      const field = fieldOfPath(issue.path);
      if (!field) continue;
      const el = document.getElementById(fieldIdOf(prefix, field === 'tried' ? 'tried.0' : field));
      if (el) return el.focus();
    }
    (errorEl ?? confirmBtn)?.focus();
  }

  async function discard() {
    if (busy || settled) return;
    busy = 'discard';
    failure = null;
    try {
      await assistantApi.discardFeatureRequest(eventId, card.id);
      ondiscarded?.(card.id);
      onremoved(card.id);
    } catch (err) {
      if ((err as ApiError)?.status === 404) onremoved(card.id);
      else failure = 'discard';
    } finally {
      busy = null;
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<article
  class="card"
  aria-label={$t('assistant.featureRequest.cardLabel', { values: { id: card.id } })}
  data-testid="feature-request-card"
  data-id={card.id}
  data-state={settled ?? (editing ? 'editing' : 'pending')}
  onkeydown={onKey}
>
  <header class="head">
    <Badge color="primary" variant="soft" size="sm">{$t('assistant.featureRequest.badge')}</Badge>
    <span class="id">{card.id}</span>
  </header>

  {#if settled}
    <div class="settled" tabindex="-1" bind:this={doneEl} data-testid="feature-request-settled">
      <p class="done">
        <span aria-hidden="true">✓</span>
        {#if settled === 'duplicate' && card.duplicate_of}
          {$t('assistant.featureRequest.joined', { values: { id: card.duplicate_of } })}
        {:else}
          {$t('assistant.featureRequest.saved', { values: { id: card.id } })}
        {/if}
      </p>
      <p class="title-line">{card.title}</p>
    </div>
  {:else}
    <p class="notice" data-testid="feature-request-notice">{$t('assistant.featureRequest.notice')}</p>

    {#if editing}
      <div class="form">
        <div class="field">
          <label for={fieldIdOf(prefix, 'title')}>{$t('assistant.featureRequest.field.title')}</label>
          <input
            id={fieldIdOf(prefix, 'title')}
            type="text"
            bind:value={form.title}
            aria-invalid={problemFor('title') ? 'true' : undefined}
            aria-describedby={describedBy('title')}
          />
          <p class="hint" id="{fieldIdOf(prefix, 'title')}-hint">
            {$t('assistant.featureRequest.count', { values: { count: Array.from(form.title.trim()).length, max: FEATURE_LIMITS.title } })}
          </p>
          {#if problemFor('title')}<p class="field-error" id="{fieldIdOf(prefix, 'title')}-error">{problemText(problemFor('title')!)}</p>{/if}
        </div>

        <div class="field">
          <label for={fieldIdOf(prefix, 'problem')}>{$t('assistant.featureRequest.field.problem')}</label>
          <textarea
            id={fieldIdOf(prefix, 'problem')}
            rows="3"
            bind:value={form.problem}
            aria-invalid={problemFor('problem') ? 'true' : undefined}
            aria-describedby={describedBy('problem')}
          ></textarea>
          <p class="hint" id="{fieldIdOf(prefix, 'problem')}-hint">
            {$t('assistant.featureRequest.count', { values: { count: Array.from(form.problem.trim()).length, max: FEATURE_LIMITS.problem } })}
          </p>
          {#if problemFor('problem')}<p class="field-error" id="{fieldIdOf(prefix, 'problem')}-error">{problemText(problemFor('problem')!)}</p>{/if}
        </div>

        <div class="field">
          <label for={fieldIdOf(prefix, 'desired')}>{$t('assistant.featureRequest.field.desired')}</label>
          <textarea
            id={fieldIdOf(prefix, 'desired')}
            rows="3"
            bind:value={form.desired}
            aria-invalid={problemFor('desired') ? 'true' : undefined}
            aria-describedby={describedBy('desired')}
          ></textarea>
          <p class="hint" id="{fieldIdOf(prefix, 'desired')}-hint">
            {$t('assistant.featureRequest.count', { values: { count: Array.from(form.desired.trim()).length, max: FEATURE_LIMITS.desired } })}
          </p>
          {#if problemFor('desired')}<p class="field-error" id="{fieldIdOf(prefix, 'desired')}-error">{problemText(problemFor('desired')!)}</p>{/if}
        </div>

        {#each form.tried as _item, i (i)}
          <div class="field">
            <label for={fieldIdOf(prefix, `tried.${i}`)}>
              {$t('assistant.featureRequest.field.triedItem', { values: { n: i + 1 } })}
            </label>
            <textarea
              id={fieldIdOf(prefix, `tried.${i}`)}
              rows="2"
              bind:value={form.tried[i]}
              aria-invalid={problemFor(`tried.${i}`) ? 'true' : undefined}
              aria-describedby={describedBy(`tried.${i}`)}
            ></textarea>
            <p class="hint" id="{fieldIdOf(prefix, `tried.${i}`)}-hint">
              {$t('assistant.featureRequest.count', { values: { count: Array.from(form.tried[i].trim()).length, max: FEATURE_LIMITS.tried } })}
            </p>
            {#if problemFor(`tried.${i}`)}<p class="field-error" id="{fieldIdOf(prefix, `tried.${i}`)}-error">{problemText(problemFor(`tried.${i}`)!)}</p>{/if}
          </div>
        {/each}

        {#if hasWorkaround}
          <div class="field">
            <label for={fieldIdOf(prefix, 'used')}>{$t('assistant.featureRequest.field.used')}</label>
            <textarea
              id={fieldIdOf(prefix, 'used')}
              rows="2"
              bind:value={form.used}
              aria-invalid={problemFor('used') ? 'true' : undefined}
              aria-describedby={describedBy('used')}
            ></textarea>
            <p class="hint" id="{fieldIdOf(prefix, 'used')}-hint">
              {$t('assistant.featureRequest.count', { values: { count: Array.from(form.used.trim()).length, max: FEATURE_LIMITS.used } })}
            </p>
            {#if problemFor('used')}<p class="field-error" id="{fieldIdOf(prefix, 'used')}-error">{problemText(problemFor('used')!)}</p>{/if}
            <label for={fieldIdOf(prefix, 'cost')}>{$t('assistant.featureRequest.field.cost')}</label>
            <select id={fieldIdOf(prefix, 'cost')} bind:value={form.cost}>
              {#each COSTS as cost (cost)}
                <option value={cost}>{costWord(cost)}</option>
              {/each}
            </select>
          </div>
        {/if}
      </div>
    {:else}
      <dl class="fields">
        <div>
          <dt>{$t('assistant.featureRequest.field.title')}</dt>
          <dd>{card.title}</dd>
        </div>
        <div>
          <dt>{$t('assistant.featureRequest.field.problem')}</dt>
          <dd>{card.problem}</dd>
        </div>
        <div>
          <dt>{$t('assistant.featureRequest.field.desired')}</dt>
          <dd>{card.desired}</dd>
        </div>
        {#if card.tried?.length}
          <div>
            <dt>{$t('assistant.featureRequest.field.tried')}</dt>
            <dd>
              <ul>
                {#each card.tried as item, i (i)}<li>{item}</li>{/each}
              </ul>
            </dd>
          </div>
        {/if}
        {#if card.workaround}
          <div>
            <dt>{$t('assistant.featureRequest.field.workaround')}</dt>
            <dd>
              {$t('assistant.featureRequest.builtAs', { values: { used: card.workaround.used, cost: costWord(card.workaround.cost) } })}
            </dd>
          </div>
        {/if}
      </dl>
      {#if card.matches_existing}
        <p class="joins" data-testid="feature-request-joins">
          {card.matches_existing.seen === 1
            ? $t('assistant.featureRequest.joinsOnce')
            : $t('assistant.featureRequest.joins', { values: { count: card.matches_existing.seen } })}
        </p>
      {/if}
    {/if}

    {#if issues.length}
      <div class="error" role="alert" tabindex="-1" bind:this={errorEl} data-testid="feature-request-invalid">
        <p>{$t('assistant.featureRequest.error.invalid')}</p>
        <ul>
          {#each issues as issue}
            {@const label = issueLabel(issue.path)}
            <li>{label ? `${label}: ` : ''}{issue.message}</li>
          {/each}
        </ul>
      </div>
    {:else if failure === 'save'}
      <p class="error" role="alert" tabindex="-1" bind:this={errorEl} data-testid="feature-request-failed">
        {$t('assistant.featureRequest.error.save')}
      </p>
    {/if}
    {#if failure === 'discard'}
      <p class="error" role="alert" data-testid="feature-request-failed">
        {$t('assistant.featureRequest.error.discard')}
      </p>
    {/if}

    <div class="actions">
      <button
        type="button"
        class="confirm"
        bind:this={confirmBtn}
        disabled={!!busy}
        onclick={confirm}
        data-testid="feature-request-confirm"
      >
        {busy === 'confirm' ? $t('assistant.featureRequest.confirming') : $t('assistant.featureRequest.confirm')}
      </button>
      {#if editing}
        <button type="button" class="quiet" disabled={!!busy} onclick={cancelEdit}>
          {$t('assistant.featureRequest.cancelEdit')}
        </button>
      {:else}
        <button
          type="button"
          class="quiet"
          bind:this={editBtn}
          disabled={!!busy || !canEdit}
          onclick={startEdit}
          data-testid="feature-request-edit"
        >
          {$t('assistant.featureRequest.edit')}
        </button>
      {/if}
      <button type="button" class="quiet" disabled={!!busy} onclick={discard} data-testid="feature-request-discard">
        {busy === 'discard' ? $t('assistant.featureRequest.discarding') : $t('assistant.featureRequest.discard')}
      </button>
    </div>
  {/if}
</article>

<style>
  .card {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-md);
    border: 1px solid var(--ink-line-2);
    background: var(--surface);
    font-size: var(--type-body-sm);
    color: var(--ink);
    min-width: 0;
  }
  .head {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  .id {
    font-size: var(--type-caption);
    color: var(--ink-soft);
  }
  .notice {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius);
    background: var(--brand-primary-tint);
    font-size: var(--type-caption);
    line-height: 1.5;
    color: var(--ink);
  }
  .fields {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin: 0;
  }
  .fields div {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .fields dt {
    font-size: var(--type-eyebrow);
    font-weight: var(--weight-bold);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-soft);
  }
  .fields dd {
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .fields ul {
    margin: 0;
    padding-left: var(--space-4);
  }
  .joins,
  .hint {
    margin: 0;
    font-size: var(--type-caption);
    color: var(--ink-soft);
  }
  .form {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .field label {
    font-weight: var(--weight-semi);
  }
  .field input,
  .field textarea,
  .field select {
    width: 100%;
    min-height: 44px;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--ink-line-2);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    box-sizing: border-box;
  }
  .field textarea {
    resize: vertical;
  }
  .field [aria-invalid='true'] {
    border-color: var(--danger);
  }
  .field-error,
  .error {
    margin: 0;
    color: var(--danger);
    font-size: var(--type-caption);
  }
  .error {
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius);
    background: var(--danger-tint);
  }
  .error p {
    margin: 0;
  }
  .error ul {
    margin: var(--space-1) 0 0;
    padding-left: var(--space-4);
  }
  .settled {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .settled:focus-visible,
  .confirm:focus-visible,
  .quiet:focus-visible,
  .field input:focus-visible,
  .field textarea:focus-visible,
  .field select:focus-visible {
    outline: 2px solid var(--brand-primary);
    outline-offset: 2px;
  }
  .done {
    margin: 0;
    font-weight: var(--weight-semi);
    color: var(--brand-accent-mid);
  }
  .title-line {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .confirm,
  .quiet {
    min-height: 44px;
    padding: 0 var(--space-4);
    border-radius: var(--radius);
    font-size: var(--type-body-sm);
    font-weight: var(--weight-semi);
    transition: background var(--motion-base);
  }
  .confirm {
    flex: 1 1 auto;
    background: var(--brand-primary);
    color: var(--surface);
  }
  .confirm:hover:not(:disabled) {
    background: var(--brand-primary-mid);
  }
  .quiet {
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--ink-line-2);
  }
  .quiet:hover:not(:disabled) {
    background: var(--surface-2);
  }
  .confirm:disabled,
  .quiet:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  @media (prefers-reduced-motion: reduce) {
    .confirm,
    .quiet {
      transition: none;
    }
  }
</style>
