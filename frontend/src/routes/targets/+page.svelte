<script lang="ts">
	import TargetCard from '$lib/components/TargetCard.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	// Placeholder data for the UI shell
	let targets = $state([
		{
			id: 'tgt-001',
			name: 'example.com',
			type: 'Domain',
			status: 'active',
			lastSeen: '2026-05-28 14:32',
			tags: ['web', 'production']
		},
		{
			id: 'tgt-002',
			name: 'api.service.dev',
			type: 'Hostname',
			status: 'active',
			lastSeen: '2026-05-28 12:15',
			tags: ['api', 'staging']
		},
		{
			id: 'tgt-003',
			name: '192.168.1.0/24',
			type: 'CIDR',
			status: 'idle',
			lastSeen: '2026-05-27 09:45',
			tags: ['internal', 'network']
		},
		{
			id: 'tgt-004',
			name: 'malicious-domain.xyz',
			type: 'Domain',
			status: 'inactive',
			lastSeen: '2026-05-25 18:20',
			tags: ['threat', 'blocked']
		}
	]);

	let selectedId = $state<string | null>(null);

	function handleTargetClick(targetId: string) {
		selectedId = targetId;
		// In production, emit event or update store
	}
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Targets Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border-0)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-lg font-semibold text-[var(--color-text-0)]">Targets</h1>
				<p class="text-xs text-[var(--color-text-2)] mt-0.5">{targets.length} targets configured</p>
			</div>
			<div class="flex items-center gap-2">
				<!-- Search -->
				<div class="relative">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-[var(--color-text-3)]" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
					</svg>
					<input
						type="text"
						placeholder="Filter targets..."
						class="pl-7 pr-3 py-1 text-xs rounded border border-[var(--color-border-0)] bg-[var(--color-bg-2)] text-[var(--color-text-1)] placeholder-[var(--color-text-3)] focus:outline-none focus:border-[var(--color-accent)] transition-colors w-40" />
				</div>

				<!-- Add button -->
				<button class="p-1.5 rounded-md border border-[var(--color-border-0)] bg-[var(--color-bg-2)] text-[var(--color-text-2)] hover:text-[var(--color-text-0)] hover:bg-[var(--color-bg-3)] transition-colors" aria-label="Add target">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
					</svg>
				</button>
			</div>
		</div>
	</div>

	<!-- Targets List -->
	<div class="flex-1 overflow-auto p-2 space-y-1">
		{#each targets as target (target.id)}
			<TargetCard
				{target}
				selected={selectedId === target.id}
				on:click={() => handleTargetClick(target.id)} />
		{/each}
	</div>

	<!-- Bottom Bar -->
	<div class="flex items-center justify-between px-3 py-2 border-t border-[var(--color-border-0)] bg-[var(--color-bg-2)] text-xs text-[var(--color-text-3)]">
		<span>{targets.length} items</span>
		<div class="flex items-center gap-2">
			<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-1)] transition-colors">
				Select All
			</button>
			<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-1)] transition-colors">
				Export
			</button>
		</div>
	</div>
</div>
