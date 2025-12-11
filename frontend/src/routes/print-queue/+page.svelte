<script lang="ts">
	import { onMount } from 'svelte';
	import { printQueueApi, sessionApi } from '$lib/api/services';
	import type { PrintQueueItem, Session } from '$lib/api/types';
	import { t } from 'svelte-i18n';
	import { EmptyState, Icon, Button, ExpandableSection, Alert } from '$lib/components/ui';
	import { PageContainer } from '$lib/components/layout';
	import PrintQueueTable from '$lib/components/domain/PrintQueueTable.svelte';
	import SessionIndicator from '$lib/components/checkin/SessionIndicator.svelte';
	import SessionSelector from '$lib/components/SessionSelector.svelte';

	let queueItems: PrintQueueItem[] = [];
	let recentlyPrintedItems: PrintQueueItem[] = [];
	let recentlyPrintedCount = 0;
	let loading = false;
	let loadingRecent = false;
	let error = '';
	let successMessage = '';
	let recentlyPrintedExpanded = false;
	let activeSession: Session | null = null;
	let activeSessions: Session[] = [];
	let showSessionSelector = false;

	onMount(async () => {
		await loadActiveSession();
		await loadQueue();
		await loadRecentlyPrintedCount();
	});

	async function loadActiveSession() {
		try {
			const sessions = await sessionApi.active();
			activeSessions = sessions;
			if (sessions.length > 0) {
				activeSession = sessions[0]; // Use the first active session
			}
		} catch (e) {
			console.error('Failed to load active session:', e);
			// Don't set error state here, as it's not critical for print queue
		}
	}

	async function loadQueue() {
		loading = true;
		error = '';
		successMessage = '';
		try {
			const allItems = await printQueueApi.getQueue();
			// Filter by session if one is selected
			if (activeSession) {
				queueItems = allItems.filter(item => item.session === activeSession.id);
			} else {
				queueItems = allItems;
			}
		} catch (e) {
			error = $t('printQueue.loadError');
			console.error('Failed to load print queue:', e);
		} finally {
			loading = false;
		}
	}

	function handleChangeSession() {
		showSessionSelector = true;
	}

	function handleSessionSelect(session: Session) {
		activeSession = session;
		showSessionSelector = false;
		loadQueue();
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

			// Refresh queue to remove from main queue
			await loadQueue();

			// Always update count, and reload items if expanded
			await loadRecentlyPrintedCount();
			if (recentlyPrintedExpanded) {
				recentlyPrintedItems = await printQueueApi.getRecentlyPrinted();
			}

			// Clear success message after 3 seconds
			setTimeout(() => {
				successMessage = '';
			}, 3000);
		} catch (e) {
			error = $t('printQueue.printError');
			console.error('Failed to mark as printed:', e);
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

	<!-- Session Indicator -->
	{#if activeSession}
		<SessionIndicator
			eventName={activeSession.event_name || 'No Event'}
			sessionName={activeSession.name || 'No Active Session'}
			sessionTime={activeSession
				? `${new Date(activeSession.start_time).toLocaleTimeString('en-US', {
						hour: '2-digit',
						minute: '2-digit',
						hour12: false,
					})} - ${activeSession.end_time ? new Date(activeSession.end_time).toLocaleTimeString('en-US', {
						hour: '2-digit',
						minute: '2-digit',
						hour12: false,
					}) : 'Open'}`
				: ''}
			showAddFamily={false}
			showChangeSession={activeSessions.length > 1}
			onChangeSession={handleChangeSession}
		/>
	{/if}

	<!-- Session Selector Modal -->
	<SessionSelector
		show={showSessionSelector}
		sessions={activeSessions}
		currentSession={activeSession}
		onSelect={handleSessionSelect}
		onClose={() => showSessionSelector = false}
	/>

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
