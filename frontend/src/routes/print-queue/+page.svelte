<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { printQueueApi } from '$lib/api/services';
	import type { PrintQueueItem, WebSocketMessage } from '$lib/api/types';
	import { t } from 'svelte-i18n';
	import { EmptyState, Icon, Button, ExpandableSection, Alert } from '$lib/components/ui';
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

	let unsubscribe: (() => void) | null = null;

	onMount(async () => {
		await loadQueue();
		await loadRecentlyPrintedCount();

		// Connect to WebSocket for real-time updates
		websocketStore.connect();
		unsubscribe = websocketStore.onMessage(handleWebSocketMessage);
	});

	onDestroy(() => {
		if (unsubscribe) {
			unsubscribe();
		}
	});

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
					qr_token: data.qr_token,
					session_name: data.session_name,
					check_in_time: data.check_in_time,
					parents: data.parents || [],
					allergies: data.allergies || undefined,
					notes: data.notes || undefined,
					label_printed: false,
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

	// Session selector removed - print queue shows all sessions

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

	async function toggleRecentlyPrinted() {
		// The bind:open already handles the toggle, we just need to load when opened
		if (recentlyPrintedExpanded) {
			await loadRecentlyPrinted();
		}
	}

	async function refreshAll() {
		await loadQueue();
		await loadRecentlyPrintedCount();
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
			qrToken: item.qr_token
		};
	}
</script>

<svelte:head>
	<title>{$t('printQueue.pageTitle')}</title>
</svelte:head>

<div class="container mx-auto p-4 max-w-7xl">
	<h1 class="text-3xl font-bold mb-6">{$t('printQueue.title')}</h1>

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
			onViewQR={(token) => window.open(`/qr/${token}`, '_blank')}
			formatTime={formatTime}
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
				onViewQR={(token) => window.open(`/qr/${token}`, '_blank')}
			/>
		{/if}
	</ExpandableSection>
</div>
