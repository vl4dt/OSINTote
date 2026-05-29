<script lang="ts">
	export let status: string;
	export let label: string = '';

	$: labelText = label || status;

	$: badgeClass = {
		'pending': 'bg-[var(--color-bg-3)] text-[var(--color-text-2)]',
		'running': 'bg-[color:rgba(88,166,255,0.15)] text-[var(--color-info)]',
		'completed': 'bg-[color:rgba(63,185,80,0.15)] text-[var(--color-success)]',
		'failed': 'bg-[color:rgba(248,81,73,0.15)] text-[var(--color-error)]',
		'canceled': 'bg-[color:rgba(210,153,34,0.15)] text-[var(--color-warning)]',
		'idle': 'bg-[var(--color-bg-3)] text-[var(--color-text-3)]'
	}[status] || 'bg-[var(--color-bg-3)] text-[var(--color-text-2)]';
</script>

<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {badgeClass}" title={status}>
	{#if status === 'running'}
		<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-info)] mr-1.5 animate-pulse"></span>
	{:else if status === 'failed'}
		<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-error)] mr-1.5"></span>
	{:else if status === 'completed'}
		<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mr-1.5"></span>
	{:else}
		<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-text-3)] mr-1.5"></span>
	{/if}
	{labelText}
</span>
