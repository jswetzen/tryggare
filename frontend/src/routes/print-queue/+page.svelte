<script lang="ts">
	import { onMount } from 'svelte';
	import { printQueueApi, sessionApi } from '$lib/api/services';
	import type { PrintQueueItem, Session } from '$lib/api/types';
	import { t } from 'svelte-i18n';
	import { EmptyState, Icon, Button, ExpandableSection, Alert } from '$lib/components/ui';
	import { PageContainer } from '$lib/components/layout';
	import PrintQueueTable from '$lib/components/domain/PrintQueueTable.svelte';
	import SessionIndicator from '$lib/components/checkin/SessionIndicator.svelte';

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
	{#if showSessionSelector}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onclick={() => showSessionSelector = false}>
			<div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4" onclick={(e) => e.stopPropagation()}>
				<div class="p-6">
					<h2 class="text-xl font-bold text-slate-900 mb-4">{$t('session.changeSession')}</h2>
					<div class="space-y-2">
						{#each activeSessions as session}
							<button
								onclick={() => handleSessionSelect(session)}
								class="w-full text-left p-4 rounded-lg border-2 transition-colors
									{activeSession?.id === session.id
										? 'border-blue-500 bg-blue-50'
										: 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'}"
							>
								<div class="font-semibold text-slate-900">{session.name}</div>
								<div class="text-sm text-slate-600">{session.event_name}</div>
								<div class="text-sm text-slate-500">
									{new Date(session.start_time).toLocaleTimeString('en-US', {
										hour: '2-digit',
										minute: '2-digit',
										hour12: false,
									})} - {session.end_time ? new Date(session.end_time).toLocaleTimeString('en-US', {
										hour: '2-digit',
										minute: '2-digit',
										hour12: false,
									}) : 'Open'}
								</div>
							</button>
						{/each}
					</div>
					<div class="mt-4 flex justify-end">
						<Button variant="ghost" onclick={() => showSessionSelector = false}>
							{$t('common.cancel')}
						</Button>
					</div>
				</div>
			</div>
		</div>
	{/if}

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
