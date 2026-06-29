<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { printQueueApi, printingApi } from '$lib/api/services';
	import type { PrintQueueItem, WebSocketMessage, Printer } from '$lib/api/types';
	import { t } from 'svelte-i18n';
	import { EmptyState, Icon, Button, ExpandableSection, Alert, PageHeader } from '$lib/components/ui';
	import { PageContainer } from '$lib/components/layout';
	import PrintQueueTable from '$lib/components/domain/PrintQueueTable.svelte';
	import { websocketStore } from '$lib/stores/websocket';

	let queueItems: PrintQueueItem[] = [];
	let recentlyPrintedItems: PrintQueueItem[] = [];
	let recentlyPrintedCount = 0;
	let loading = false;
	let loadingRecent = false;
	let error = '';
	let successMessage = '';
	let recentlyPrintedExpanded = false;
	let printers: Printer[] = [];

	let unsubscribe: (() => void) | null = null;

	onMount(async () => {
		await loadQueue();
		await Promise.all([loadRecentlyPrintedCount(), loadPrinters()]);

		// Connect to WebSocket for real-time updates
		websocketStore.connect();
		unsubscribe = websocketStore.onMessage(handleWebSocketMessage);
	});

	onDestroy(() => {
		if (unsubscribe) {
			unsubscribe();
		}
	});

	async function loadPrinters() {
		try {
			printers = await printingApi.getPrinters();
		} catch (e) {
			console.error('Failed to load printers:', e);
		}
	}

	function handleWebSocketMessage(message: WebSocketMessage) {
		if (message.type === 'child_checked_in') {
			// Add new check-in to print queue
			const data = message.data;

			// Only add if we have the enriched data from backend
			if (data.parents !== undefined) {
				const newItem: PrintQueueItem = {
					id: data.record_id,
					child_name: data.child_name,
					child_last_name: data.child_last_name,
					qr_code: data.qr_code,
					session_name: data.session_name,
					check_in_time: data.check_in_time,
					parents: data.parents || [],
					allergies: data.allergies || undefined,
					notes: data.notes || undefined,
					label_printed: false,
					print_job: null,
				};

				// Add to queue (at beginning for most recent first)
				// Avoid duplicates
				if (!queueItems.find(item => item.id === newItem.id)) {
					queueItems = [newItem, ...queueItems];
				}
			} else {
				// Fallback: fetch from API if enriched data not available
				fetchSingleQueueItem(data.record_id);
			}
		}
		else if (message.type === 'child_checked_out' || message.type === 'checkin_undone') {
			// Remove from queue
			const recordId = message.data?.record_id;
			queueItems = queueItems.filter(item => item.id !== recordId);

			// Also update recently printed if item was there
			if (recentlyPrintedExpanded) {
				recentlyPrintedItems = recentlyPrintedItems.filter(item => item.id !== recordId);
				recentlyPrintedCount = recentlyPrintedItems.length;
			}
		}
		else if (message.type === 'print_job_completed') {
			const recordId = message.data?.record_id;
			if (recordId) {
				const printedItem = queueItems.find(item => item.id === recordId);
				queueItems = queueItems.filter(item => item.id !== recordId);
				if (printedItem) {
					recentlyPrintedCount += 1;
					if (recentlyPrintedExpanded) {
						recentlyPrintedItems = [{ ...printedItem, label_printed: true }, ...recentlyPrintedItems];
					}
				}
			}
		}
		else if (message.type === 'printer_status_changed' || message.type === 'printer_registered') {
			const { uuid, name, is_online } = message.data;
			const existing = printers.find((p) => p.id === uuid);
			if (existing) {
				printers = printers.map((p) =>
					p.id === uuid ? { ...p, name, is_online } : p
				);
			} else if (is_online) {
				printers = [...printers, { id: uuid, name, is_online }];
			}
		}
	}

	async function fetchSingleQueueItem(recordId: string) {
		try {
			const items = await printQueueApi.getQueue();
			const item = items.find(i => i.id === recordId);
			if (item && !queueItems.find(i => i.id === recordId)) {
				queueItems = [item, ...queueItems];
			}
		} catch (err) {
			console.error('Failed to fetch queue item:', err);
		}
	}

	async function loadQueue() {
		loading = true;
		error = '';
		successMessage = '';
		try {
			queueItems = await printQueueApi.getQueue();
			// Show all items regardless of session - staff need to see all pending labels
		} catch (e) {
			error = $t('printQueue.loadError');
			console.error('Failed to load print queue:', e);
		} finally {
			loading = false;
		}
	}

	async function loadRecentlyPrintedCount() {
		try {
			const items = await printQueueApi.getRecentlyPrinted();
			recentlyPrintedCount = items.length;
		} catch (e) {
			console.error('Failed to load recently printed count:', e);
		}
	}

	async function loadRecentlyPrinted() {
		loadingRecent = true;
		try {
			recentlyPrintedItems = await printQueueApi.getRecentlyPrinted();
			recentlyPrintedCount = recentlyPrintedItems.length;
		} catch (e) {
			console.error('Failed to load recently printed:', e);
		} finally {
			loadingRecent = false;
		}
	}

	async function printLabel(checkinId: string) {
		// Open print page in new window
		const printUrl = printQueueApi.getPrintPageUrl(checkinId);
		window.open(printUrl, '_blank');

		// Mark as printed immediately
		try {
			await printQueueApi.markSinglePrinted(checkinId);
			successMessage = $t('printQueue.printSuccess');

			// Optimistic removal from queue
			const printedItem = queueItems.find(item => item.id === checkinId);
			queueItems = queueItems.filter(item => item.id !== checkinId);

			// Update recently printed
			await loadRecentlyPrintedCount();
			if (recentlyPrintedExpanded && printedItem) {
				recentlyPrintedItems = [{ ...printedItem, label_printed: true }, ...recentlyPrintedItems];
			}

			// Clear success message after 3 seconds
			setTimeout(() => {
				successMessage = '';
			}, 3000);
		} catch (e) {
			error = $t('printQueue.printError');
			console.error('Failed to mark as printed:', e);
			// Reload on error
			await loadQueue();
		}
	}

	async function assignPrinter(checkinId: string, printerId: string) {
		try {
			// The item may live in the pending queue or in the recently-printed
			// list (reprinting a lost label). Reuse an existing job if there is
			// one; otherwise create a fresh job for the printer.
			const item =
				queueItems.find(i => i.id === checkinId) ||
				recentlyPrintedItems.find(i => i.id === checkinId);
			let job;
			if (item?.print_job?.id) {
				job = await printingApi.assignJob(item.print_job.id, printerId);
			} else {
				job = await printingApi.createJob({ checkin_id: checkinId, printer_id: printerId });
			}
			const newJob = {
				id: job.id,
				printer: job.printer,
				printer_name: job.printer_name,
				status: job.status,
			};
			// Update whichever list holds the item with the new job info.
			queueItems = queueItems.map(i =>
				i.id === checkinId ? { ...i, print_job: newJob } : i
			);
			recentlyPrintedItems = recentlyPrintedItems.map(i =>
				i.id === checkinId ? { ...i, print_job: newJob } : i
			);
			successMessage = $t('printQueue.printSuccess');
			setTimeout(() => { successMessage = ''; }, 3000);
		} catch (e) {
			error = String(e);
			console.error('Failed to assign printer:', e);
		}
	}

	async function toggleRecentlyPrinted() {
		if (recentlyPrintedExpanded) {
			await loadRecentlyPrinted();
		}
	}

	async function refreshAll() {
		await loadQueue();
		await loadRecentlyPrintedCount();
		await loadPrinters();
		if (recentlyPrintedExpanded) {
			recentlyPrintedItems = await printQueueApi.getRecentlyPrinted();
		}
	}

	function formatTime(isoString: string): string {
		const date = new Date(isoString);
		return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}

	// Transform API data to component format
	function transformItem(item: PrintQueueItem) {
		return {
			id: item.id,
			childName: `${item.child_name} ${item.child_last_name}`,
			parentNames: item.parents?.map((p) => p.name).join(', ') || '',
			sessionName: item.session_name,
			checkInTime: item.check_in_time,
			allergies: item.allergies,
			qrCode: item.qr_code,
			printJob: item.print_job,
		};
	}
</script>

<svelte:head>
	<title>{$t('printQueue.pageTitle')}</title>
</svelte:head>

<div class="min-h-screen bg-neutral-100">
	<div class="max-w-4xl mx-auto p-3 md:p-5">
		<PageHeader title={$t('printQueue.title')} />

		<!-- Error and Success Messages -->
	{#if error}
		<Alert type="error" dismissible ondismiss={() => error = ''}>
			{error}
		</Alert>
	{/if}

	{#if successMessage}
		<Alert type="success" dismissible ondismiss={() => successMessage = ''}>
			{successMessage}
		</Alert>
	{/if}

	<!-- Action Bar -->
	<div class="flex justify-end mb-4">
		<Button variant="ghost" onclick={refreshAll}>
			<Icon name="refresh" size="sm" class="mr-2" />
			{$t('common.refresh')}
		</Button>
	</div>

	{#if loading}
		<EmptyState type="loading" title={$t('common.loading')} />
	{:else if queueItems.length === 0}
		<EmptyState
			type="empty"
			title={$t('printQueue.empty')}
			description={$t('printQueue.emptyDescription')}
		>
			{#snippet icon()}
				<Icon name="check-circle" size="xl" />
			{/snippet}
		</EmptyState>
	{:else}
		<!-- Queue Table -->
		<PrintQueueTable
			items={queueItems.map(transformItem)}
			columns={['childName', 'session', 'actions']}
			onPrint={printLabel}
			onViewQR={(code) => window.open(`/qr/${code}`, '_blank')}
			onAssignPrinter={printers.length > 0 ? assignPrinter : undefined}
			{printers}
			{formatTime}
		/>

		<!-- Helper Text -->
		<Alert type="info" class="mt-6">
			{$t('printQueue.clickPrintToLabel')}
		</Alert>
	{/if}

	<!-- Recently Printed Section -->
	<ExpandableSection
		bind:expanded={recentlyPrintedExpanded}
		title={$t('printQueue.recentlyPrinted')}
		count={recentlyPrintedCount}
		hint={$t('printQueue.clickToExpand')}
		class="mt-6"
		ontoggle={toggleRecentlyPrinted}
	>
		{#if loadingRecent}
			<EmptyState type="loading" title={$t('common.loading')} />
		{:else if recentlyPrintedItems.length === 0}
			<EmptyState type="empty" title={$t('printQueue.noRecentlyPrinted')} />
		{:else}
			<PrintQueueTable
				items={recentlyPrintedItems.map(transformItem)}
				columns={['childName', 'actions']}
				onPrint={printLabel}
				onViewQR={(code) => window.open(`/qr/${code}`, '_blank')}
				onAssignPrinter={printers.length > 0 ? assignPrinter : undefined}
				{printers}
				{formatTime}
			/>
		{/if}
	</ExpandableSection>
	</div>
</div>
