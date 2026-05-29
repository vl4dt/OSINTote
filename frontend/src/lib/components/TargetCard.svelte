<script lang="ts">
	let { target, selected = false, onClick }: {
		target: { id: string; name: string; type: string; status?: string; lastSeen?: string; tags?: string[]; recordCount?: number; taskCount?: number };
		selected?: boolean;
		onClick: (e: MouseEvent) => void;
	} = $props();

	const cardClass = $derived(
		selected
			? 'border-[var(--color-accent)] bg-[color:rgba(88,166,255,0.08)] shadow-sm'
			: 'border-[var(--color-border-0)] bg-[var(--color-bg-2)] hover:border-[var(--color-border-1)] hover:bg-[var(--color-bg-3)]'
	);

	const statusDotClass = $derived(
		target.status === 'active' ? 'bg-[var(--color-success)]' :
		target.status === 'inactive' ? 'bg-[var(--color-text-3)]' :
		'bg-[var(--color-warning)]'
	);
</script>

<button
	class="w-full text-left p-3 rounded-md border transition-all {cardClass}"
	onclick={onClick}>
	<div class="flex items-start justify-between gap-2 mb-1.5">
		<span class="text-sm font-medium text-[var(--color-text-0)] truncate">
			{target.name}
		</span>
		{#if target.status}
			<span class="shrink-0">
				<!-- Inline StatusBadge would go here, simplified for now -->
				<span class="inline-block w-2 h-2 rounded-full
					{target.status === 'active' ? 'bg-[var(--color-success)]' :
					 target.status === 'inactive' ? 'bg-[var(--color-text-3)]' :
					 'bg-[var(--color-warning)]'}"
					title={target.status}></span>
			</span>
		{/if}
	</div>

	<div class="flex items-center gap-1.5 text-xs text-[var(--color-text-2)]">
		<code class="text-[var(--color-text-3)]">{target.id}</code>
		<span class="text-[var(--color-text-3)]">•</span>
		<span>{target.type}</span>
	</div>

	{#if target.lastSeen}
		<div class="mt-1 text-xs text-[var(--color-text-3)]">
			Last seen: {target.lastSeen}
		</div>
	{/if}

	{#if target.tags && target.tags.length > 0}
		<div class="mt-1.5 flex flex-wrap gap-1">
			{#each target.tags as tag}
				<span class="px-1.5 py-0.5 text-xs rounded bg-[var(--color-bg-3)] text-[var(--color-text-2)]">
					{tag}
				</span>
			{/each}
		</div>
	{/if}
</button>
