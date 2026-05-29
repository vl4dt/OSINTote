<script lang="ts">
	import { onMount } from 'svelte';
	import type { Result } from '$lib/types';
	import { apiService } from '$lib/api/real';
	import ResultRow from '$lib/components/ResultRow.svelte';
	import ResultDetail from '$lib/components/ResultDetail.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	let results = $state<Result[]>([]);
	let filteredResults = $state<Result[]>([]);
	let selectedId = $state<string | null>(null);
	let detailResult = $state<Result | null>(null);
	let loading = $state(true);
	let expandDetail = $state(false);

	let severityFilter = $state<string>('all');
	let typeFilter = $state<string>('all');
	let searchQuery = $state('');

	const resultTypes = $derived(
		[...new Set(results.map(r => r.type))] as string[]
	);

	async function loadResults(): Promise<void> {
		loading = true;
		try {
			results = await apiService.getResults();
		} finally {
			loading = false;
			applyFilters();
		}
	}

	function applyFilters(): void {
		let result = [...results];

		if (severityFilter !== 'all') {
			result = result.filter(r => r.severity === severityFilter);
		}

		if (typeFilter !== 'all') {
			result = result.filter(r => r.type === typeFilter);
		}

		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase();
			result = result.filter(r =>
				r.message.toLowerCase().includes(q) ||
				r.id.toLowerCase().includes(q) ||
				r.target.toLowerCase().includes(q) ||
				r.taskId.toLowerCase().includes(q)
			);
		}

		filteredResults = result;
	}

	function handleResultClick(result: Result): void {
		if (selectedId === result.id) {
			selectedId = null;
			detailResult = null;
			expandDetail = false;
		} else {
			selectedId = result.id;
			detailResult = result;
			expandDetail = true;
		}
	}

	function handleSeverityChange(e: Event): void {
		severityFilter = (e.target as HTMLSelectElement).value;
		applyFilters();
	}

	function handleTypeChange(e: Event): void {
		typeFilter = (e.target as HTMLSelectElement).value;
		applyFilters();
	}

	function handleSearchInput(e: Event): void {
		searchQuery = (e.target as HTMLInputElement).value;
		applyFilters();
	}

	function handleCloseDetail(): void {
		selectedId = null;
		detailResult = null;
		expandDetail = false;
	}

	const severityCounts = $derived({
		critical: results.filter(r => r.severity === 'critical').length,
		high: results.filter(r => r.severity === 'high').length,
		warning: results.filter(r => r.severity === 'warning').length,
		info: results.filter(r => r.severity === 'info').length
	});

	function handleExportJSON(): void {
		const data = JSON.stringify(filteredResults, null, 2);
		const blob = new Blob([data], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'osintote-results.json';
		a.click();
		URL.revokeObjectURL(url);
	}

	onMount(() => {
		loadResults();
	});
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between gap-2">
			<div>
				<h1 class="text-lg font-semibold text-[var(--color-text-primary)]">Results</h1>
				<p class="text-xs text-[var(--color-text-secondary)] mt-0.5">{results.length} findings</p>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<!-- Severity Filter -->
				<select
					value={severityFilter}
					onchange={handleSeverityChange}
					class="px-2 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)] transition-colors">
					<option value="all">All Severities</option>
					<option value="critical">Critical</option>
					<option value="high">High</option>
					<option value="warning">Warning</option>
					<option value="info">Info</option>
				</select>

				<!-- Type Filter -->
				<select
					value={typeFilter}
					onchange={handleTypeChange}
					class="px-2 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)] transition-colors">
					<option value="all">All Types</option>
					{#each resultTypes as type}
						<option value={type}>{type}</option>
					{/each}
				</select>

				<!-- Search -->
				<div class="relative">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
					</svg>
					<input
						type="text"
						value={searchQuery}
						oninput={handleSearchInput}
						placeholder="Search results..."
						class="pl-7 pr-3 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] transition-colors w-36" />
				</div>

				<!-- Export -->
				<button
					class="px-2.5 py-1 text-xs font-medium rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-3)] transition-colors"
					onclick={handleExportJSON}>
					Export JSON
				</button>
			</div>
		</div>
	</div>

	<!-- Severity Summary Bar -->
	{#if results.length > 0}
		<div class="flex items-center gap-3 px-4 py-1.5 border-b border-[var(--color-border)] bg-[var(--color-bg-2)] text-xs">
			<span class="text-[var(--color-text-muted)]">Summary:</span>
			<span class="flex items-center gap-1 text-[var(--color-error)]">
				<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-error)]"></span>
				{severityCounts.critical} critical
			</span>
			<span class="flex items-center gap-1 text-[var(--color-warning)]">
				<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-warning)]"></span>
				{severityCounts.high} high
			</span>
			<span class="flex items-center gap-1 text-[var(--color-warning)]">
				<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-warning)]"></span>
				{severityCounts.warning} warning
			</span>
			<span class="flex items-center gap-1 text-[var(--color-info)]">
				<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-info)]"></span>
				{severityCounts.info} info
			</span>
		</div>
	{/if}

	<!-- Content -->
	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<div class="flex flex-col items-center gap-2">
				<div class="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
				<span class="text-xs text-[var(--color-text-muted)]">Loading results...</span>
			</div>
		</div>
	{:else if filteredResults.length === 0}
		<EmptyState
			title={searchQuery || severityFilter !== 'all' || typeFilter !== 'all' ? 'No matching results' : 'No results yet'}
			description={searchQuery || severityFilter !== 'all' || typeFilter !== 'all' ? 'Try adjusting your filters' : 'Results will appear here after running tasks.'} />
	{:else}
		<div class="flex-1 overflow-auto p-2 space-y-1">
			{#each filteredResults as result (result.id)}
				<ResultRow
					{result}
					selected={selectedId === result.id}
					onToggle={() => handleResultClick(result)} />
			{/each}
		</div>
	{/if}

	<!-- Bottom Bar -->
	{#if filteredResults.length > 0}
		<div class="flex items-center justify-between px-3 py-2 border-t border-[var(--color-border)] bg-[var(--color-bg-2)] text-xs text-[var(--color-text-muted)]">
			<span>{filteredResults.length} of {results.length} findings</span>
			<div class="flex items-center gap-2">
				<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-primary)] transition-colors">
					Select All
				</button>
				<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-primary)] transition-colors">
					Export
				</button>
			</div>
		</div>
	{/if}

	<!-- Result Detail Panel (right slot) -->
	{#if detailResult}
		<ResultDetail result={detailResult} onClose={handleCloseDetail} />
	{/if}
</div>
