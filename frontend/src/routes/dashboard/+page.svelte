<script lang="ts">
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
</script>

<div class="flex flex-col h-full overflow-auto">
	<!-- Dashboard Header -->
	<div class="px-6 py-4 border-b border-[var(--color-border-0)] bg-[var(--color-bg-1)]">
		<h1 class="text-lg font-semibold text-[var(--color-text-0)]">Dashboard</h1>
		<p class="text-sm text-[var(--color-text-2)] mt-1">Overview of your OSINT operations</p>
	</div>

	<!-- Stats Grid -->
	<div class="px-6 py-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
		<div class="p-3 rounded-lg border border-[var(--color-border-0)] bg-[var(--color-bg-2)]">
			<div class="flex items-center justify-between mb-2">
				<span class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-2)]">Targets</span>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-[var(--color-text-3)]" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" />
				</svg>
			</div>
			<div class="text-2xl font-bold text-[var(--color-text-0)]">0</div>
			<div class="text-xs text-[var(--color-text-3)]">Active</div>
		</div>

		<div class="p-3 rounded-lg border border-[var(--color-border-0)] bg-[var(--color-bg-2)]">
			<div class="flex items-center justify-between mb-2">
				<span class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-2)]">Tasks</span>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-[var(--color-text-3)]" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V4a2 2 0 00-2-2H6zm1 3H5v3h2V5zm5 0h-2v3h2V5z" clip-rule="evenodd" />
				</svg>
			</div>
			<div class="text-2xl font-bold text-[var(--color-text-0)]">0</div>
			<div class="text-xs text-[var(--color-text-3)]">Total</div>
		</div>

		<div class="p-3 rounded-lg border border-[var(--color-border-0)] bg-[var(--color-bg-2)]">
			<div class="flex items-center justify-between mb-2">
				<span class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-2)]">Running</span>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-[var(--color-text-3)]" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
				</svg>
			</div>
			<div class="text-2xl font-bold text-[var(--color-success)]">0</div>
			<div class="text-xs text-[var(--color-text-3)]">Active tasks</div>
		</div>

		<div class="p-3 rounded-lg border border-[var(--color-border-0)] bg-[var(--color-bg-2)]">
			<div class="flex items-center justify-between mb-2">
				<span class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-2)]">Results</span>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-[var(--color-text-3)]" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 10.828l1.293 1.293a1 1 0 001.414-1.414L12.414 11H15a2 2 0 002-2V5a1 1 0 10-2 0v1H9V3z" clip-rule="evenodd" />
				</svg>
			</div>
			<div class="text-2xl font-bold text-[var(--color-text-0)]">0</div>
			<div class="text-xs text-[var(--color-text-3)]">Total findings</div>
		</div>
	</div>

	<!-- Recent Activity -->
	<div class="flex-1 px-6 py-4">
		<h2 class="text-sm font-semibold text-[var(--color-text-1)] mb-3">Recent Activity</h2>

		{#if true}
			<div class="rounded-lg border border-[var(--color-border-0)] bg-[var(--color-bg-2)] overflow-hidden">
				<EmptyState
					title="No recent activity"
					description="Start by adding a target or creating a task to begin your OSINT investigation."
					actionLabel="Add Target" />
			</div>
		{/if}
	</div>
</div>
