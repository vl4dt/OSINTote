<script lang="ts">
	import { onMount } from 'svelte';
	import type { Target } from '$lib/types';
	import { apiService } from '$lib/api/real';
	import TargetCard from '$lib/components/TargetCard.svelte';
	import TargetDetail from '$lib/components/TargetDetail.svelte';
	import TargetDialog from '$lib/components/TargetDialog.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	let targets = $state<Target[]>([]);
	let filteredTargets = $state<Target[]>([]);
	let searchQuery = $state('');
	let selectedId = $state<string | null>(null);
	let detailTarget = $state<Target | null>(null);
	let showAddDialog = $state(false);
	let loading = $state(true);

	let statusFilter = $state<string>('all');

	async function loadTargets(): Promise<void> {
		loading = true;
		try {
			targets = await apiService.getTargets();
		} finally {
			loading = false;
			applyFilters();
		}
	}

	function applyFilters(): void {
		let result = [...targets];

		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase();
			result = result.filter(t =>
				t.name.toLowerCase().includes(q) ||
				t.id.toLowerCase().includes(q) ||
				t.tags.some(tag => tag.includes(q))
			);
		}

		if (statusFilter !== 'all') {
			result = result.filter(t => t.status === statusFilter);
		}

		filteredTargets = result;
	}

	function handleSearchInput(e: Event): void {
		searchQuery = (e.target as HTMLInputElement).value;
		applyFilters();
	}

	function handleTargetClick(target: Target): void {
		selectedId = target.id;
		detailTarget = target;
	}

	function handleTargetCloseDetail(): void {
		selectedId = null;
		detailTarget = null;
	}

	async function handleCreateTarget(data: { name: string; type: string; tags: string[] }): Promise<void> {
		await apiService.createTarget({
			name: data.name,
			type: data.type as Target['type'],
			status: 'active',
			tags: data.tags
		});
		showAddDialog = false;
		await loadTargets();
	}

	function handleDeleteTarget(id: string): void {
		apiService.deleteTarget(id);
		targets = targets.filter(t => t.id !== id);
		if (selectedId === id) {
			selectedId = null;
			detailTarget = null;
		}
		applyFilters();
	}

	// (delete is handled inline in the page)

	onMount(() => {
		loadTargets();
	});
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between gap-2">
			<div>
				<h1 class="text-lg font-semibold text-[var(--color-text-primary)]">Targets</h1>
				<p class="text-xs text-[var(--color-text-secondary)] mt-0.5">{targets.length} targets configured</p>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<!-- Search -->
				<div class="relative">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
					</svg>
					<input
						type="text"
						value={searchQuery}
						oninput={handleSearchInput}
						placeholder="Filter targets..."
						class="pl-7 pr-3 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] transition-colors w-36" />
				</div>

				<!-- Status Filter -->
				<select
					value={statusFilter}
					onchange={(e) => { statusFilter = (e.target as HTMLSelectElement).value; applyFilters(); }}
					class="px-2 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)] transition-colors">
					<option value="all">All Status</option>
					<option value="active">Active</option>
					<option value="inactive">Inactive</option>
					<option value="idle">Idle</option>
				</select>

				<!-- Add button -->
				<button
					class="p-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-3)] transition-colors"
					aria-label="Add target"
					onclick={() => { showAddDialog = true; }}
					title="Add target">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
					</svg>
				</button>
			</div>
		</div>
	</div>

	<!-- Content -->
	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<div class="flex flex-col items-center gap-2">
				<div class="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
				<span class="text-xs text-[var(--color-text-muted)]">Loading targets...</span>
			</div>
		</div>
	{:else if filteredTargets.length === 0}
		<EmptyState
			title={searchQuery || statusFilter !== 'all' ? 'No matching targets' : 'No targets configured'}
			description={searchQuery || statusFilter !== 'all' ? 'Try adjusting your filters' : 'Add your first target to start reconnaissance.'}
			actionLabel={targets.length === 0 ? 'Add Target' : undefined}
			onAction={() => targets.length === 0 && (showAddDialog = true)} />
	{:else}
		<div class="flex-1 overflow-auto p-2 space-y-1">
			{#each filteredTargets as target (target.id)}
				<TargetCard
					{target}
					selected={selectedId === target.id}
					onClick={() => handleTargetClick(target)} />
			{/each}
		</div>
	{/if}

	<!-- Bottom Bar -->
	{#if filteredTargets.length > 0}
		<div class="flex items-center justify-between px-3 py-2 border-t border-[var(--color-border)] bg-[var(--color-bg-2)] text-xs text-[var(--color-text-muted)]">
			<span>{filteredTargets.length} of {targets.length} targets</span>
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

	<!-- Target Detail Panel (right slot of AppShell) -->
	{#if detailTarget}
		<TargetDetail target={detailTarget} onClose={handleTargetCloseDetail} />
	{/if}

	<!-- Add/Edit Dialog -->
	<TargetDialog
		open={showAddDialog}
		onClose={() => { showAddDialog = false; }}
		onSubmit={handleCreateTarget} />
</div>
