<script lang="ts">
	let { status, label = '' } = $props();

	const labelText = $derived(label || status);

	const badgeClass = $derived(
		status === 'running' ? 'bg-[color:rgba(88,166,255,0.15)] text-[var(--color-info)]' :
		status === 'completed' ? 'bg-[color:rgba(63,185,80,0.15)] text-[var(--color-success)]' :
		status === 'failed' ? 'bg-[color:rgba(248,81,73,0.15)] text-[var(--color-error)]' :
		status === 'canceled' ? 'bg-[color:rgba(210,153,34,0.15)] text-[var(--color-warning)]' :
		status === 'pending' || status === 'queued' || status === 'idle'
			? 'bg-[var(--color-bg-3)] text-[var(--color-text-2)]'
			: 'bg-[var(--color-bg-3)] text-[var(--color-text-2)]'
	);

	const dotClass = $derived(
		status === 'running' ? 'bg-[var(--color-info)] animate-pulse' :
		status === 'failed' ? 'bg-[var(--color-error)]' :
		status === 'completed' ? 'bg-[var(--color-success)]' :
		status === 'canceled' ? 'bg-[var(--color-warning)]' :
		'bg-[var(--color-text-3)]'
	);
</script>

<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {badgeClass}" title={status}>
	<span class="w-1.5 h-1.5 rounded-full {dotClass} mr-1.5"></span>
	{labelText}
</span>
