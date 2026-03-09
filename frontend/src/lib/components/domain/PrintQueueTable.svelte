<script lang="ts">
  import { Button, Icon, Badge } from '$lib/components/ui';
  import { t } from 'svelte-i18n';
  import type { Printer } from '$lib/api/types';

  // Transformed print queue item for display
  interface PrintQueueDisplayItem {
    id: string;
    childName: string;
    parentNames: string;
    sessionName: string;
    checkInTime: string;
    allergies?: string;
    qrCode: string | null;
    printJob?: {
      id: string;
      printer: string | null;
      printer_name: string | null;
      status: string;
    } | null;
  }

  interface Props {
    items: PrintQueueDisplayItem[];
    columns?: ('childName' | 'session' | 'checkInTime' | 'allergies' | 'actions')[];
    onPrint: (id: string) => void;
    onViewQR: (code: string) => void;
    onAssignPrinter?: (checkinId: string, printerId: string) => void;
    printers?: Printer[];
    formatTime?: (isoString: string) => string;
  }

  let {
    items,
    columns = ['childName', 'session', 'checkInTime', 'allergies', 'actions'],
    onPrint,
    onViewQR,
    onAssignPrinter,
    printers = [],
    formatTime = (iso) => new Date(iso).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })
  }: Props = $props();

  const showColumn = (col: string) => columns.includes(col as any);

  // Track which row has the printer popover open
  let openPopoverItemId = $state<string | null>(null);

  function togglePopover(itemId: string) {
    openPopoverItemId = openPopoverItemId === itemId ? null : itemId;
  }

  function selectPrinter(checkinId: string, printerId: string) {
    onAssignPrinter?.(checkinId, printerId);
    openPopoverItemId = null;
  }

  const onlinePrinters = $derived(printers.filter((p) => p.is_online));
</script>

<div class="bg-white rounded-lg border-2 border-slate-300 overflow-hidden">
  <table class="w-full">
    <thead class="bg-slate-50 border-b-2 border-slate-300">
      <tr>
        {#if showColumn('childName')}
          <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
            {$t('printQueue.childName')}
          </th>
        {/if}
        {#if showColumn('session')}
          <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
            {$t('printQueue.session')}
          </th>
        {/if}
        {#if showColumn('checkInTime')}
          <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
            {$t('printQueue.time')}
          </th>
        {/if}
        {#if showColumn('allergies')}
          <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
            {$t('printQueue.allergies')}
          </th>
        {/if}
        {#if showColumn('actions')}
          <th class="px-4 py-3 text-center text-sm font-medium text-slate-700">
            {$t('printQueue.actions')}
          </th>
        {/if}
      </tr>
    </thead>
    <tbody>
      {#each items as item}
        <tr class="border-b border-slate-200 hover:bg-slate-50">
          {#if showColumn('childName')}
            <td class="px-4 py-3">
              <div class="font-semibold text-slate-900">{item.childName}</div>
              <div class="text-sm text-slate-500">{item.parentNames}</div>
            </td>
          {/if}
          {#if showColumn('session')}
            <td class="px-4 py-3 text-sm text-slate-700">{item.sessionName}</td>
          {/if}
          {#if showColumn('checkInTime')}
            <td class="px-4 py-3 text-sm text-slate-700">{formatTime(item.checkInTime)}</td>
          {/if}
          {#if showColumn('allergies')}
            <td class="px-4 py-3">
              {#if item.allergies}
                <Badge color="danger" variant="soft" size="sm">
                  {item.allergies}
                </Badge>
              {:else}
                <span class="text-slate-400 text-sm">{$t('printQueue.none')}</span>
              {/if}
            </td>
          {/if}
          {#if showColumn('actions')}
            <td class="px-4 py-3">
              <div class="flex gap-2 justify-center flex-wrap">
                <Button size="sm" variant="primary" onclick={() => onPrint(item.id)}>
                  <Icon name="printer" size="sm" class="mr-1" />
                  {$t('printQueue.print')}
                </Button>

                <!-- Printer assign button (only shown when printers are available and handler provided) -->
                {#if onAssignPrinter && printers.length > 0}
                  <div class="relative">
                    {#if item.printJob?.printer_name && (item.printJob.status === 'pending' || item.printJob.status === 'sent')}
                      <!-- Job assigned: show status + resend button -->
                      <Button
                        size="sm"
                        variant="ghost"
                        onclick={() => togglePopover(item.id)}
                        title={$t('printing.resend')}
                      >
                        <Icon name="printer" size="sm" class="mr-1 text-green-600" />
                        <span class="text-green-700 text-xs">{item.printJob.printer_name}</span>
                      </Button>
                    {:else}
                      <!-- No job or completed/failed: assign printer -->
                      <Button
                        size="sm"
                        variant="ghost"
                        onclick={() => togglePopover(item.id)}
                      >
                        <Icon name="printer" size="sm" class="mr-1" />
                        {$t('printing.assignPrinter')}
                      </Button>
                    {/if}

                    <!-- Popover with printer list -->
                    {#if openPopoverItemId === item.id}
                      <div
                        class="absolute right-0 top-full mt-1 z-10 bg-white border border-slate-200 rounded-lg shadow-lg min-w-40 py-1"
                      >
                        {#if onlinePrinters.length === 0}
                          <div class="px-3 py-2 text-sm text-slate-500">
                            {$t('printing.noPrinters')}
                          </div>
                        {:else}
                          {#each onlinePrinters as printer}
                            <button
                              class="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 text-slate-700"
                              onclick={() => selectPrinter(item.id, printer.id)}
                            >
                              {printer.name}
                            </button>
                          {/each}
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/if}

                {#if item.qrCode}
                <Button
                  size="sm"
                  variant="ghost"
                  onclick={() => onViewQR(item.qrCode!)}
                >
                  <Icon name="qr-code" size="sm" class="mr-1" />
                  {$t('printQueue.viewQR')}
                </Button>
                {/if}
              </div>
            </td>
          {/if}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
