<script lang="ts">
  /**
   * The floating chat on the register page (assistant mode only; the page
   * loads this file with a dynamic import). It owns presentation and the
   * review/apply flow; the page owns the store's lifecycle and the preview.
   *
   * Joining a run already in progress: the server stores a reply only when
   * the run ends, so a tab that connects mid-run shows the saved transcript
   * plus whatever streams from then on. Text written before the join, and the
   * message being answered, appear once the run finishes and the transcript is
   * re-read. The store never keeps a partial text over the stored one.
   */
  import { onDestroy, tick } from 'svelte';
  import { t } from 'svelte-i18n';
  import { fromStore } from 'svelte/store';
  import { assistantApi } from '$lib/api/assistantService';
  import Icon from '$lib/components/ui/Icon.svelte';
  import type { AssistantStore } from './assistantStore';
  import { ERROR_CODES, isRetryable, refusalReason } from './helpers';
  import ChatMessage from './ChatMessage.svelte';
  import ChatComposer from './ChatComposer.svelte';
  import DraftReview from './DraftReview.svelte';
  import PersonalDataNotice from './PersonalDataNotice.svelte';
  import ToolProgress from './ToolProgress.svelte';

  let {
    eventId,
    store,
    previewStale = false,
    previewDraftUnusable = false,
    reload
  }: {
    eventId: string;
    store: AssistantStore;
    // previewSource is the page's own badge; the review reads the draft itself.
    previewSource?: 'draft' | 'saved';
    previewStale?: boolean;
    previewDraftUnusable?: boolean;
    reload: () => Promise<void> | void;
  } = $props();

  const PANEL_WIDTH = 384;
  const GAP = 16;
  const storageKey = `assistant.ui.${eventId}`;
  const examples = ['1', '2', '3'];

  const live = fromStore(store);
  const s = $derived(live.current);

  // Only {open} is stored, never message text.
  function readOpen(): boolean {
    try {
      return JSON.parse(localStorage.getItem(storageKey) ?? '{}').open === true;
    } catch {
      return false;
    }
  }

  let open = $state(readOpen());
  let unread = $state(false);
  let draftText = $state('');
  let lastSent = $state('');
  let confirmingClear = $state(false);
  let clearBusy = $state(false);
  let clearFailed = $state(false);
  let noticeBusy = $state(false);
  let noticeFailed = $state(false);
  let wide = $state(false);

  let launcherEl = $state<HTMLButtonElement | null>(null);
  let inputEl = $state<HTMLTextAreaElement | null>(null);
  let acceptEl = $state<HTMLButtonElement | null>(null);
  let bodyEl = $state<HTMLDivElement | null>(null);

  $effect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ open }));
    } catch {
      /* private mode: the state just does not persist */
    }
  });

  // A reply that finished while minimized leaves a dot on the launcher.
  let wasRunning = false;
  $effect(() => {
    const running = s.running;
    if (wasRunning && !running && !open) unread = true;
    wasRunning = running;
  });

  // On wide screens the page makes room instead of being covered: the form
  // is centred, so padding on <body> moves it clear of the fixed panel.
  $effect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const q = window.matchMedia('(min-width: 1024px)');
    wide = q.matches;
    const on = () => (wide = q.matches);
    q.addEventListener?.('change', on);
    return () => q.removeEventListener?.('change', on);
  });
  $effect(() => {
    if (!(open && wide)) return;
    document.body.style.paddingInlineEnd = `${PANEL_WIDTH + 2 * GAP}px`;
    return () => {
      document.body.style.paddingInlineEnd = '';
    };
  });
  onDestroy(() => {
    if (typeof document !== 'undefined') document.body.style.paddingInlineEnd = '';
  });

  async function show() {
    open = true;
    unread = false;
    await tick();
    (s.noticeRequired ? acceptEl : inputEl)?.focus();
    scrollDown(true);
  }
  async function minimize() {
    open = false;
    await tick();
    launcherEl?.focus();
  }

  function onPanelKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation();
      void minimize();
    }
  }

  // Stay at the bottom while text streams, unless the reader scrolled up.
  function scrollDown(force = false) {
    const el = bodyEl;
    if (!el) return;
    if (force || el.scrollHeight - el.scrollTop - el.clientHeight < 80) el.scrollTop = el.scrollHeight;
  }
  $effect(() => {
    s.transcript;
    s.tools;
    s.error;
    s.warnings;
    void tick().then(() => scrollDown());
  });

  function send(text: string) {
    if (store.send(text)) {
      lastSent = text;
      draftText = '';
    }
  }
  function retry() {
    if (lastSent) store.send(lastSent);
  }
  function sendAnyway(w: { replyTo: string; text: string }) {
    store.dismissWarning(w.replyTo);
    if (store.send(w.text, { confirmPersonalData: true })) lastSent = w.text;
  }
  function editWarned(w: { replyTo: string; text: string }) {
    store.dismissWarning(w.replyTo);
    draftText = w.text;
    void tick().then(() => inputEl?.focus());
  }
  function useExample(key: string) {
    draftText = $t(`assistant.empty.${key}`);
    inputEl?.focus();
  }

  async function acceptNotice() {
    noticeBusy = true;
    noticeFailed = false;
    try {
      await assistantApi.acceptNotice(eventId);
      store.acceptedNotice();
      await tick();
      inputEl?.focus();
    } catch {
      noticeFailed = true;
    } finally {
      noticeBusy = false;
    }
  }

  async function clearConversation() {
    clearBusy = true;
    clearFailed = false;
    try {
      await assistantApi.clearConversation(eventId);
      confirmingClear = false;
      lastSent = '';
      await store.refresh();
      await reload();
    } catch {
      clearFailed = true;
    } finally {
      clearBusy = false;
    }
  }

  const errorKey = $derived(
    s.error ? `assistant.error.${(ERROR_CODES as readonly string[]).includes(s.error.code) ? s.error.code : 'unknown'}` : null
  );
  // A primitive derived: `s` changes identity on every event, this does not.
  const draftVersion = $derived(s.draftVersion);
  const warning = $derived(s.warnings[s.warnings.length - 1] ?? null);
  const refused = $derived(s.connection === 'refused');
  const offline = $derived(s.connection === 'reconnecting' || s.connection === 'connecting');
  const hasContent = $derived(s.transcript.length > 0 || draftVersion > 0);

  // One polite line for screen readers. It never says "draft updated": the
  // page's own status region announces "Preview updated" for that.
  const statusText = $derived(
    errorKey ? $t(errorKey) : warning ? $t('assistant.piiWarning') : s.running ? $t('assistant.working') : ''
  );
</script>

{#if !open}
  <button
    bind:this={launcherEl}
    type="button"
    class="launcher"
    aria-expanded="false"
    aria-controls="assistant-panel"
    aria-label={unread ? `${$t('assistant.open')}. ${$t('assistant.unread')}` : $t('assistant.open')}
    onclick={show}
    data-testid="assistant-launcher"
  >
    <Icon name="chat" size="md" />
    <span class="launcher-label">{$t('assistant.open')}</span>
    {#if unread}<span class="dot" data-testid="assistant-unread" aria-hidden="true"></span>{/if}
  </button>
{:else}
  <!-- Non-modal on purpose: testers type into the form while the chat is open. -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <section
    id="assistant-panel"
    class="panel"
    aria-label={$t('assistant.title')}
    onkeydown={onPanelKey}
    data-testid="assistant-panel"
  >
    <header class="header">
      <div class="heading">
        <h2 class="title">{$t('assistant.title')}</h2>
        <p class="subtitle">{$t('assistant.subtitle')}</p>
      </div>
      {#if hasContent && !refused}
        <button
          type="button"
          class="icon-btn"
          aria-label={$t('assistant.clear')}
          title={$t('assistant.clear')}
          onclick={() => (confirmingClear = !confirmingClear)}
          aria-expanded={confirmingClear}
          data-testid="assistant-clear"
        >
          <Icon name="trash" size="sm" />
        </button>
      {/if}
      <button
        type="button"
        class="icon-btn"
        aria-label={$t('assistant.minimize')}
        title={$t('assistant.minimize')}
        onclick={minimize}
        data-testid="assistant-minimize"
      >
        <Icon name="chevron-down" size="sm" />
      </button>
    </header>

    {#if confirmingClear}
      <div class="confirm" data-testid="assistant-clear-confirm">
        <p>{$t('assistant.clearConfirm')}</p>
        {#if clearFailed}<p class="failed">{$t('assistant.clearFailed')}</p>{/if}
        <div class="confirm-actions">
          <button type="button" class="danger" disabled={clearBusy} onclick={clearConversation}>
            {$t('assistant.clearYes')}
          </button>
          <button type="button" class="quiet" disabled={clearBusy} onclick={() => (confirmingClear = false)}>
            {$t('assistant.clearNo')}
          </button>
        </div>
      </div>
    {/if}

    {#if offline}
      <p class="offline" data-testid="assistant-offline">
        {s.connection === 'connecting' ? $t('assistant.connection.connecting') : $t('assistant.connection.reconnecting')}
      </p>
    {/if}

    <div class="body" bind:this={bodyEl}>
      {#if refused}
        <div class="unavailable" data-testid="assistant-unavailable">
          <h3>{$t('assistant.unavailable.title')}</h3>
          <p>{$t(`assistant.unavailable.${refusalReason(s.refusedCode)}`)}</p>
        </div>
      {:else}
        {#if s.noticeRequired}
          <PersonalDataNotice onaccept={acceptNotice} busy={noticeBusy} failed={noticeFailed} bind:acceptEl />
        {:else if s.transcript.length === 0 && !s.running}
          <div class="empty" data-testid="assistant-empty">
            <h3>{$t('assistant.empty.title')}</h3>
            <p>{$t('assistant.empty.body')}</p>
            <p class="eyebrow">{$t('assistant.empty.examples')}</p>
            <ul class="examples">
              {#each examples as key}
                <li>
                  <button type="button" onclick={() => useExample(key)}>{$t(`assistant.empty.${key}`)}</button>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        <div
          role="log"
          aria-label={$t('assistant.title')}
          aria-live="polite"
          aria-busy={s.running}
          class="log"
          data-testid="assistant-log"
        >
          {#each s.transcript as entry, i (entry.id ?? `${entry.runId ?? 'h'}-${i}`)}
            <ChatMessage role={entry.role} text={entry.text} />
          {/each}
        </div>

        {#if s.running}
          <div class="working" data-testid="assistant-working">
            <p><span class="pulse" aria-hidden="true"></span>{$t('assistant.working')}</p>
            <ToolProgress tools={s.tools} />
          </div>
        {/if}

        {#if warning}
          <div class="pii" data-testid="assistant-pii">
            <p>{$t('assistant.piiWarning')}</p>
            <div class="pii-actions">
              <button type="button" class="quiet" onclick={() => sendAnyway(warning)}>{$t('assistant.piiSend')}</button>
              <button type="button" class="quiet" onclick={() => editWarned(warning)}>{$t('assistant.piiEdit')}</button>
            </div>
          </div>
        {/if}

        {#if errorKey}
          <div class="error" data-testid="assistant-error" data-code={s.error?.code}>
            <p>{$t(errorKey)}</p>
            {#if s.error && isRetryable(s.error.code) && lastSent && !s.running}
              <button type="button" class="quiet" onclick={retry}>{$t('assistant.retry')}</button>
            {/if}
          </div>
        {/if}
      {/if}
    </div>

    {#if !refused}
      <DraftReview
        {eventId}
        version={draftVersion}
        draftUnusable={previewDraftUnusable}
        pageStale={previewStale}
        running={s.running}
        {reload}
      />
      <div class="footer">
        <ChatComposer
          bind:value={draftText}
          bind:inputEl
          running={s.running}
          disabled={s.noticeRequired}
          sendDisabled={s.connection !== 'open'}
          onsend={send}
          oncancel={() => store.cancel()}
        />
      </div>
    {/if}

    <p class="sr-only" role="status" data-testid="assistant-status">{statusText}</p>
  </section>
{/if}

<style>
  /* Layout. Below 768px the panel is a full sheet; from 1024px it is a side
     column and the page moves over (see the body padding effect). */
  .launcher,
  .panel {
    position: fixed;
    z-index: 40;
    right: max(var(--space-4), env(safe-area-inset-right));
    bottom: max(var(--space-4), env(safe-area-inset-bottom));
  }
  .launcher {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    min-height: 48px;
    padding: 0 var(--space-5) 0 var(--space-4);
    border-radius: var(--radius-pill);
    background: var(--brand-primary);
    color: var(--surface);
    font-weight: var(--weight-semi);
    box-shadow: var(--shadow-sm);
    transition: transform var(--motion-base), background var(--motion-base), box-shadow var(--motion-base);
    animation: appear var(--motion-base);
  }
  .launcher:hover {
    background: var(--brand-primary-mid);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  .launcher:focus-visible,
  .icon-btn:focus-visible,
  .examples button:focus-visible,
  .quiet:focus-visible,
  .danger:focus-visible {
    outline: 2px solid var(--brand-primary);
    outline-offset: 2px;
  }
  .dot {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--surface);
    border: 3px solid var(--brand-primary-mid);
  }
  @media (max-width: 639px) {
    .launcher {
      width: 52px;
      height: 52px;
      padding: 0;
      justify-content: center;
    }
    .launcher-label {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
    }
  }

  .panel {
    display: flex;
    flex-direction: column;
    width: 384px;
    height: min(640px, calc(100dvh - 2 * var(--space-4)));
    border-radius: var(--radius-md);
    background: var(--surface);
    border: 1px solid var(--ink-line);
    box-shadow: var(--shadow-md);
    overflow: hidden;
    animation: appear var(--motion-base);
  }
  @media (min-width: 1024px) {
    .panel {
      top: var(--space-4);
      height: auto;
    }
  }
  @media (max-width: 767px) {
    .panel {
      inset: 0;
      width: auto;
      height: 100dvh;
      border-radius: 0;
      border: 0;
      padding-bottom: env(safe-area-inset-bottom);
    }
  }
  @keyframes appear {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .launcher,
    .panel {
      animation: none;
      transition: none;
    }
    .launcher:hover {
      transform: none;
    }
  }

  .header {
    display: flex;
    align-items: flex-start;
    gap: var(--space-1);
    padding: var(--space-4) var(--space-3) var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--ink-line);
  }
  .heading {
    flex: 1;
    min-width: 0;
  }
  .title {
    margin: 0;
    font-size: var(--type-body);
    font-weight: var(--weight-bold);
    color: var(--ink);
  }
  .subtitle {
    margin: 2px 0 0;
    font-size: var(--type-caption);
    color: var(--ink-soft);
  }
  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    margin: -6px 0;
    border-radius: var(--radius);
    color: var(--ink-soft);
    transition: background var(--motion-base), color var(--motion-base);
  }
  .icon-btn:hover {
    background: var(--surface-2);
    color: var(--ink);
  }

  .confirm {
    padding: var(--space-3) var(--space-4);
    background: var(--danger-tint);
    font-size: var(--type-body-sm);
    color: var(--ink);
  }
  .confirm p {
    margin: 0 0 var(--space-2);
  }
  .confirm .failed {
    color: var(--danger);
  }
  .confirm-actions,
  .pii-actions {
    display: flex;
    gap: var(--space-2);
  }
  .quiet,
  .danger {
    min-height: 36px;
    padding: 0 var(--space-3);
    border-radius: var(--radius);
    font-size: var(--type-body-sm);
    font-weight: var(--weight-semi);
    border: 1px solid var(--ink-line-2);
    background: var(--surface);
    color: var(--ink);
  }
  .quiet:hover {
    background: var(--surface-2);
  }
  .danger {
    background: var(--danger);
    border-color: var(--danger);
    color: var(--surface);
  }
  .offline {
    margin: 0;
    padding: var(--space-2) var(--space-4);
    background: var(--surface-2);
    color: var(--ink-soft);
    font-size: var(--type-caption);
    text-align: center;
  }

  .body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
  }
  .log {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .empty h3,
  .unavailable h3 {
    margin: 0 0 var(--space-1);
    font-size: var(--type-body);
    font-weight: var(--weight-bold);
  }
  .empty p,
  .unavailable p {
    margin: 0 0 var(--space-3);
    font-size: var(--type-body-sm);
    line-height: 1.5;
    color: var(--ink-soft);
  }
  .eyebrow {
    margin: var(--space-4) 0 var(--space-2) !important;
    font-size: var(--type-eyebrow) !important;
    font-weight: var(--weight-bold);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-soft) !important;
  }
  .examples {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .examples button {
    width: 100%;
    min-height: 44px;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--ink-line-2);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--ink);
    font-size: var(--type-body-sm);
    text-align: left;
    transition: background var(--motion-base), border-color var(--motion-base);
  }
  .examples button:hover {
    background: var(--brand-primary-tint);
    border-color: var(--brand-primary);
  }

  .working {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .working p {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin: 0;
    font-size: var(--type-body-sm);
    color: var(--ink-soft);
  }
  .pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--brand-primary);
    animation: pulse 1.2s ease-in-out infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.3;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .pulse {
      animation: none;
    }
  }

  .pii,
  .error {
    padding: var(--space-3);
    border-radius: var(--radius-md);
    font-size: var(--type-body-sm);
  }
  .pii {
    background: var(--surface-2);
    border: 1px solid var(--ink-line-2);
  }
  .error {
    background: var(--danger-tint);
    color: var(--danger);
  }
  .pii p,
  .error p {
    margin: 0 0 var(--space-2);
  }
  .error p:last-child {
    margin-bottom: 0;
  }

  .footer {
    padding: var(--space-3) var(--space-4) var(--space-4);
    border-top: 1px solid var(--ink-line);
  }
</style>
