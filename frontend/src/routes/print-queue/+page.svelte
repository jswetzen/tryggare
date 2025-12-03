<script lang="ts">
	import { onMount } from 'svelte';
	import { printQueueApi } from '$lib/api/services';
	import type { PrintQueueItem } from '$lib/api/types';
	import { t } from 'svelte-i18n';

	let queueItems: PrintQueueItem[] = [];
	let recentlyPrintedItems: PrintQueueItem[] = [];
	let loading = false;
	let loadingRecent = false;
	let error = '';
	let successMessage = '';
	let recentlyPrintedExpanded = false;

	onMount(async () => {
		await loadQueue();
	});

	async function loadQueue() {
		loading = true;
		error = '';
		successMessage = '';
		try {
			queueItems = await printQueueApi.getQueue();
		} catch (e) {
			error = $t('printQueue.loadError');
			console.error('Failed to load print queue:', e);
		} finally {
			loading = false;
		}
	}

	async function loadRecentlyPrinted() {
		loadingRecent = true;
		try {
			recentlyPrintedItems = await printQueueApi.getRecentlyPrinted();
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

			// Refresh recently printed if expanded
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
		if (recentlyPrintedExpanded) {
			recentlyPrintedItems = await printQueueApi.getRecentlyPrinted();
		}
	}

	function formatTime(isoString: string): string {
		const date = new Date(isoString);
		return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}
</script>

<svelte:head>
	<title>{$t('printQueue.pageTitle')}</title>
</svelte:head>

<div class="container mx-auto p-4 max-w-7xl">
	<h1 class="text-3xl font-bold mb-6">{$t('printQueue.title')}</h1>

	<!-- Error and Success Messages -->
	{#if error}
		<div class="alert alert-error mb-4 shadow-lg">
			<div>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="stroke-current flex-shrink-0 h-6 w-6"
					fill="none"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>{error}</span>
			</div>
			<button class="btn btn-sm btn-ghost" on:click={() => (error = '')}>✕</button>
		</div>
	{/if}

	{#if successMessage}
		<div class="alert alert-success mb-4 shadow-lg">
			<div>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="stroke-current flex-shrink-0 h-6 w-6"
					fill="none"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>{successMessage}</span>
			</div>
		</div>
	{/if}

	<!-- Action Bar -->
	<div class="flex justify-end mb-4">
		<button class="btn btn-ghost" on:click={refreshAll}>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 mr-2"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
				/>
			</svg>
			{$t('common.refresh')}
		</button>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-12">
			<span class="loading loading-spinner loading-lg"></span>
			<span class="ml-4 text-lg">{$t('common.loading')}</span>
		</div>
	{:else if queueItems.length === 0}
		<div class="text-center py-12">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-24 w-24 mx-auto text-gray-400 mb-4"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
			<p class="text-xl text-gray-600 font-semibold">{$t('printQueue.empty')}</p>
			<p class="text-gray-500 mt-2">{$t('printQueue.emptyDescription')}</p>
		</div>
	{:else}
		<!-- Queue Table -->
		<div class="overflow-x-auto bg-base-100 shadow-xl rounded-lg">
			<table class="table table-zebra w-full">
				<thead>
					<tr>
						<th>{$t('printQueue.childName')}</th>
						<th>{$t('printQueue.session')}</th>
						<th>{$t('printQueue.checkInTime')}</th>
						<th>{$t('printQueue.allergies')}</th>
						<th>{$t('printQueue.actions')}</th>
					</tr>
				</thead>
				<tbody>
					{#each queueItems as item}
						<tr class="hover">
							<td>
								<div class="font-bold">
									{item.child_name}
									{item.child_last_name}
								</div>
								{#if item.parents && item.parents.length > 0}
									<div class="text-sm opacity-70">
										{item.parents.map((p) => p.name).join(', ')}
									</div>
								{/if}
							</td>
							<td>{item.session_name}</td>
							<td>{formatTime(item.check_in_time)}</td>
							<td>
								{#if item.allergies}
									<span class="badge badge-error badge-sm">{item.allergies}</span>
								{:else}
									<span class="text-gray-400">-</span>
								{/if}
							</td>
							<td>
								<div class="flex gap-2">
									<button class="btn btn-primary btn-sm" on:click={() => printLabel(item.id)}>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="h-4 w-4 mr-1"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
											/>
										</svg>
										{$t('printQueue.print')}
									</button>
									<a
										href="/qr/{item.qr_token}"
										target="_blank"
										class="btn btn-ghost btn-sm"
										rel="noopener noreferrer"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="h-4 w-4 mr-1"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
											/>
										</svg>
										{$t('printQueue.viewQR')}
									</a>
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Helper Text -->
		<div class="alert alert-info mt-6 shadow-lg">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				class="stroke-current flex-shrink-0 w-6 h-6"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
				></path>
			</svg>
			<span>{$t('printQueue.clickPrintToLabel')}</span>
		</div>
	{/if}

	<!-- Recently Printed Section -->
	<div class="mt-8">
		<details bind:open={recentlyPrintedExpanded} on:toggle={toggleRecentlyPrinted}>
			<summary class="cursor-pointer text-xl font-bold mb-4 flex items-center gap-2">
				{$t('printQueue.recentlyPrintedCount', { values: { count: recentlyPrintedItems.length } })}
				<span class="badge badge-neutral">{recentlyPrintedItems.length}</span>
			</summary>

			{#if loadingRecent}
				<div class="flex justify-center items-center py-8">
					<span class="loading loading-spinner loading-md"></span>
					<span class="ml-4">{$t('common.loading')}</span>
				</div>
			{:else if recentlyPrintedItems.length === 0}
				<div class="text-center py-8 text-gray-500">
					{$t('printQueue.noRecentlyPrinted')}
				</div>
			{:else}
				<div class="overflow-x-auto bg-base-100 shadow-xl rounded-lg">
					<table class="table table-zebra w-full">
						<thead>
							<tr>
								<th>{$t('printQueue.childName')}</th>
								<th>{$t('printQueue.actions')}</th>
							</tr>
						</thead>
						<tbody>
							{#each recentlyPrintedItems as item}
								<tr class="hover">
									<td>
										<div class="font-bold">
											{item.child_name}
											{item.child_last_name}
										</div>
										{#if item.parents && item.parents.length > 0}
											<div class="text-sm opacity-70">
												{item.parents.map((p) => p.name).join(', ')}
											</div>
										{/if}
									</td>
									<td>
										<div class="flex gap-2">
											<button class="btn btn-primary btn-sm" on:click={() => printLabel(item.id)}>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													class="h-4 w-4 mr-1"
													fill="none"
													viewBox="0 0 24 24"
													stroke="currentColor"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
													/>
												</svg>
												{$t('printQueue.print')}
											</button>
											<a
												href="/qr/{item.qr_token}"
												target="_blank"
												class="btn btn-ghost btn-sm"
												rel="noopener noreferrer"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													class="h-4 w-4 mr-1"
													fill="none"
													viewBox="0 0 24 24"
													stroke="currentColor"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
													/>
												</svg>
												{$t('printQueue.viewQR')}
											</a>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</details>
	</div>
</div>
