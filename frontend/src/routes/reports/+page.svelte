<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { eventApi, reportApi } from '$lib/api/services';
  // Aliased: the domain `Event` would otherwise shadow the DOM `Event` that
  // the change handlers below are typed against.
  import type { EventReportListItem, EventReport, Event as AppEvent } from '$lib/api/types';
  import { PageHeader, Select, Button } from '$lib/components/ui';
  import { PERMISSION, hasPermission } from '$lib/auth/permissions';

  let { data } = $props();

  /**
   * Reading a report and taking a new one are different permissions, so the
   * whole generate panel is absent — not disabled — for a user who only holds
   * the read. Server-side `reports.add_eventreport` is the real guarantee;
   * this only avoids offering an action that would 403.
   */
  const canGenerate = $derived(hasPermission(data.user, PERMISSION.addReports));

  let reports = $state<EventReportListItem[]>([]);
  let selectedId = $state<string>('');
  let detail = $state<EventReport | null>(null);
  let loading = $state(true);
  let detailLoading = $state(false);
  let error = $state<string | null>(null);

  let events = $state<AppEvent[]>([]);
  let generateEventId = $state<string>('');
  let generating = $state(false);
  let generateError = $state<string | null>(null);
  let generateSuccess = $state(false);

  // Fixed display order for age buckets (matches the backend snapshot keys).
  const AGE_ORDER = ['0-2', '3-5', '6-8', '9-12', '13+', 'unknown'];

  onMount(async () => {
    await load();
    if (canGenerate) await loadEvents();
  });

  async function loadEvents() {
    try {
      events = await eventApi.list();
    } catch (e) {
      // A failure here costs the generate panel its event list, but the
      // reports themselves are already on screen and still readable. Leaving
      // `events` empty renders the "no events" line, which is honest enough
      // without turning a side-feature's outage into a page-level error.
      console.error('Failed to load events', e);
    }
  }

  async function generate() {
    // Generation is not idempotent — every call appends a snapshot — so a
    // double-click would silently create two. The disabled attribute alone
    // does not cover the in-flight window.
    if (generating || !generateEventId) return;
    generating = true;
    generateError = null;
    generateSuccess = false;
    try {
      const report = await reportApi.generate(generateEventId);
      // Re-fetch rather than splicing the new report in: the list serializer
      // returns different fields from the detail one, and the list is ordered
      // server-side.
      reports = await reportApi.list();
      selectedId = report.id;
      detail = report;
      generateSuccess = true;
    } catch (e) {
      console.error('Failed to generate report', e);
      generateError = $t('reports.generateError');
    } finally {
      generating = false;
    }
  }

  async function load() {
    loading = true;
    error = null;
    try {
      reports = await reportApi.list();
      if (reports.length > 0) {
        selectedId = reports[0].id;
        await loadDetail(selectedId);
      }
    } catch (e) {
      console.error('Failed to load reports', e);
      error = $t('reports.loadError');
    } finally {
      loading = false;
    }
  }

  async function loadDetail(id: string) {
    detailLoading = true;
    error = null;
    try {
      detail = await reportApi.get(id);
    } catch (e) {
      console.error('Failed to load report detail', e);
      error = $t('reports.loadError');
    } finally {
      detailLoading = false;
    }
  }

  function onSelect(event: Event) {
    const id = (event.target as HTMLSelectElement).value;
    selectedId = id;
    if (id) loadDetail(id);
  }

  const eventOptions = $derived([
    { value: '', label: $t('reports.generateEventPlaceholder') },
    ...events.map((e) => ({ value: e.id, label: e.name }))
  ]);

  const reportOptions = $derived(
    reports.map((r) => ({
      value: r.id,
      label: `${r.event_name} — ${formatPickerDateTime(r.generated_at)}`
    }))
  );

  function formatDateTime(iso: string): string {
    return new Date(iso).toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  /**
   * Seconds, unlike the display format above, because this label is the only
   * thing telling two snapshots apart. Generating used to be an admin action
   * taken rarely; it is now one click, so two snapshots of the same event
   * within a minute are easy to produce — and to the minute they render as two
   * identical options with no way to know which is which.
   */
  function formatPickerDateTime(iso: string): string {
    return new Date(iso).toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  }

  function formatSessionTime(iso: string): string {
    return new Date(iso).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  function num(v: number | null | undefined): string {
    return v === null || v === undefined ? '—' : String(v);
  }
</script>

<svelte:head>
  <title>{$t('reports.pageTitle')}</title>
</svelte:head>

<div class="max-w-7xl mx-auto">
  <PageHeader title={$t('reports.title')}>
    {#snippet actions()}
      {#if detail}
        <a
          href={reportApi.exportUrl(detail.id, 'csv')}
          class="px-4 py-2 rounded-button font-semibold bg-primary-600 text-white hover:bg-primary-700 transition-colors"
        >
          {$t('reports.exportCsv')}
        </a>
        <a
          href={reportApi.exportUrl(detail.id, 'json')}
          class="px-4 py-2 rounded-button font-semibold border border-neutral-300 text-neutral-700 hover:bg-neutral-100 transition-colors"
        >
          {$t('reports.exportJson')}
        </a>
      {/if}
    {/snippet}
  </PageHeader>

  <p class="text-neutral-600 mb-5">{$t('reports.subtitle')}</p>

  {#if error}
    <div class="mb-4 rounded-lg border border-danger-300 bg-danger-50 text-danger-700 px-4 py-3">
      {error}
    </div>
  {/if}

  <!--
    Deliberately outside the `reports.length === 0` branch below: an event with
    no snapshot yet is exactly when someone needs this, and putting it inside
    the list would make the empty state a dead end again.
  -->
  {#if canGenerate}
    <section
      class="mb-6 rounded-card border border-neutral-200 bg-white p-4"
      aria-labelledby="generate-report-heading"
    >
      <h2 id="generate-report-heading" class="text-base font-bold text-neutral-800">
        {$t('reports.generateHeading')}
      </h2>
      <p class="mt-1 mb-3 text-sm text-neutral-600">{$t('reports.generateHelp')}</p>

      {#if events.length === 0}
        <p class="text-sm text-neutral-500">{$t('reports.generateNoEvents')}</p>
      {:else}
        <div class="flex flex-wrap items-end gap-3">
          <div class="min-w-64 flex-1">
            <Select
              label={$t('reports.generateEvent')}
              options={eventOptions}
              value={generateEventId}
              onchange={(e: Event) =>
                (generateEventId = (e.target as HTMLSelectElement).value)}
            />
          </div>
          <Button onclick={generate} disabled={generating || !generateEventId} loading={generating}>
            {generating ? $t('reports.generating') : $t('reports.generate')}
          </Button>
        </div>
      {/if}

      {#if generateError}
        <div
          class="mt-3 rounded-button border border-danger-300 bg-danger-50 px-3 py-2 text-sm text-danger-700"
          role="alert"
        >
          {generateError}
        </div>
      {:else if generateSuccess}
        <div
          class="mt-3 rounded-button border border-success-300 bg-success-50 px-3 py-2 text-sm text-success-700"
          role="status"
        >
          ✓ {$t('reports.generateSuccess')}
        </div>
      {/if}
    </section>
  {/if}

  {#if loading}
    <div class="text-neutral-600">{$t('reports.loading')}</div>
  {:else if reports.length === 0}
    <div class="rounded-lg border border-neutral-200 bg-white px-6 py-10 text-center text-neutral-600">
      {$t('reports.noReports')}
    </div>
  {:else}
    <div class="mb-6 max-w-xl">
      <Select
        label={$t('reports.selectReport')}
        options={reportOptions}
        value={selectedId}
        onchange={onSelect}
      />
    </div>

    {#if detailLoading}
      <div class="text-neutral-600">{$t('reports.loading')}</div>
    {:else if detail}
      {@const ev = detail.data.event}
      <div class="mb-4 text-sm text-neutral-500">
        {$t('reports.generated')}
        {formatDateTime(detail.generated_at)}
        {#if detail.generated_by_name}
          {$t('reports.by')} {detail.generated_by_name}
        {/if}
      </div>

      <!-- Overview -->
      <section class="mb-8">
        <h2 class="text-lg font-bold text-neutral-800 mb-3">{$t('reports.overview')}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
            <div class="text-3xl font-bold text-primary-900">{num(ev.unique_children)}</div>
            <div class="text-sm text-neutral-600">{$t('reports.uniqueChildren')}</div>
          </div>
          <div class="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
            <div class="text-3xl font-bold text-primary-900">{num(ev.total_checkins)}</div>
            <div class="text-sm text-neutral-600">{$t('reports.totalCheckins')}</div>
          </div>
          <div class="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
            <div class="text-3xl font-bold text-primary-900">{num(ev.session_count)}</div>
            <div class="text-sm text-neutral-600">{$t('reports.sessionsCount')}</div>
          </div>
          <div class="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
            <div class="text-3xl font-bold text-primary-900">{num(ev.operations.avg_stay_minutes)}</div>
            <div class="text-sm text-neutral-600">{$t('reports.avgStay')}</div>
          </div>
        </div>
      </section>

      <div class="grid md:grid-cols-3 gap-6 mb-8">
        <!-- Ticketing -->
        <section class="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
          <h2 class="text-lg font-bold text-neutral-800 mb-3">{$t('reports.tickets')}</h2>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.eventPasses')}</dt><dd class="font-semibold">{num(ev.tickets.event_passes_issued)}</dd></div>
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.sessionTickets')}</dt><dd class="font-semibold">{num(ev.tickets.session_tickets_issued)}</dd></div>
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.eventNoShows')}</dt><dd class="font-semibold">{num(ev.tickets.event_pass_no_shows)}</dd></div>
          </dl>
        </section>

        <!-- Demographics -->
        <section class="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
          <h2 class="text-lg font-bold text-neutral-800 mb-3">{$t('reports.demographics')}</h2>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.withAllergies')}</dt><dd class="font-semibold">{num(ev.demographics.with_allergies)}</dd></div>
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.returningFamilies')}</dt><dd class="font-semibold">{num(ev.demographics.returning_families)}</dd></div>
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.newFamilies')}</dt><dd class="font-semibold">{num(ev.demographics.new_families)}</dd></div>
          </dl>
          <div class="mt-3 pt-3 border-t border-neutral-100">
            <div class="text-xs font-semibold text-neutral-500 uppercase mb-2">{$t('reports.ageGroups')}</div>
            <div class="grid grid-cols-3 gap-2 text-center">
              {#each AGE_ORDER as bucket}
                <div class="bg-neutral-50 rounded p-2">
                  <div class="font-bold text-neutral-800">{num(ev.demographics.age_buckets[bucket])}</div>
                  <div class="text-xs text-neutral-500">{bucket}</div>
                </div>
              {/each}
            </div>
          </div>
        </section>

        <!-- Operations -->
        <section class="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
          <h2 class="text-lg font-bold text-neutral-800 mb-3">{$t('reports.operations')}</h2>
          <dl class="space-y-2 text-sm mb-3">
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.labelsPrinted')}</dt><dd class="font-semibold">{num(ev.operations.labels_printed)}</dd></div>
            <div class="flex justify-between"><dt class="text-neutral-600">{$t('reports.avgStay')}</dt><dd class="font-semibold">{num(ev.operations.avg_stay_minutes)}</dd></div>
          </dl>
          <div class="pt-3 border-t border-neutral-100">
            <div class="text-xs font-semibold text-neutral-500 uppercase mb-2">{$t('reports.checkinsPerStaff')}</div>
            {#if ev.operations.checkins_per_staff.length === 0}
              <div class="text-sm text-neutral-400">—</div>
            {:else}
              <dl class="space-y-1 text-sm">
                {#each ev.operations.checkins_per_staff as row}
                  <div class="flex justify-between"><dt class="text-neutral-600">{row.staff}</dt><dd class="font-semibold">{row.count}</dd></div>
                {/each}
              </dl>
            {/if}
          </div>
        </section>
      </div>

      <!-- Per-session table -->
      <section>
        <h2 class="text-lg font-bold text-neutral-800 mb-3">{$t('reports.sessions')}</h2>
        <div class="overflow-x-auto bg-white rounded-lg shadow-sm border border-neutral-200">
          <table class="min-w-full text-sm">
            <thead class="bg-neutral-50 text-neutral-600 text-left">
              <tr>
                <th class="px-3 py-2 font-semibold">{$t('reports.session')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.uniqueChildren')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.totalCheckins')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.peakConcurrent')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.supervised')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.staffedCheckouts')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.sessionTickets')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.sessionNoShows')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.labelsPrinted')}</th>
                <th class="px-3 py-2 font-semibold text-right">{$t('reports.avgStay')}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each detail.data.sessions as s}
                <tr class="hover:bg-neutral-50">
                  <td class="px-3 py-2">
                    <div class="font-semibold text-neutral-800">{s.name}</div>
                    <div class="text-xs text-neutral-500">{formatSessionTime(s.start_time)}</div>
                  </td>
                  <td class="px-3 py-2 text-right">{num(s.unique_children)}</td>
                  <td class="px-3 py-2 text-right">{num(s.total_checkins)}</td>
                  <td class="px-3 py-2 text-right">{num(s.peak_concurrent)}</td>
                  <td class="px-3 py-2 text-right">{num(s.supervised)}</td>
                  <td class="px-3 py-2 text-right">{num(s.staffed_checkouts)}</td>
                  <td class="px-3 py-2 text-right">{num(s.session_tickets_issued)}</td>
                  <td class="px-3 py-2 text-right">{num(s.session_ticket_no_shows)}</td>
                  <td class="px-3 py-2 text-right">{num(s.labels_printed)}</td>
                  <td class="px-3 py-2 text-right">{num(s.avg_stay_minutes)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}
  {/if}
</div>
