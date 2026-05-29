<script lang="ts">
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let { target, onClose }: {
		target: { id: string; name: string; type: string; status: string; lastSeen?: string; tags: string[]; recordCount?: number; taskCount?: number; createdAt?: string; updatedAt?: string };
		onClose: () => void;
	} = $props();

	const typeColor = $derived(
		target.type === 'domain' ? 'text-[var(--color-accent)]' :
		target.type === 'ip' || target.type === 'cidr' ? 'text-[var(--color-success)]' :
		target.type === 'email' ? 'text-[var(--color-warning)]' :
		target.type === 'url' ? 'text-[var(--color-error)]' :
		'text-[var(--color-text-secondary)]'
	);

	const typeEmoji = $derived(
		target.type === 'domain' ? '🌐' :
		target.type === 'hostname' ? '🏷️' :
		target.type === 'ip' ? '💻' :
		target.type === 'cidr' ? '🔢' :
		target.type === 'email' ? '📧' :
		target.type === 'url' ? '🔗' :
		'🎯'
	);

	const statusEmoji = $derived(
		target.status === 'active' ? '🟢' :
		target.status === 'inactive' ? '🔴' :
		'⚪'
	);
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between">
			<h2 class="text-sm font-semibold text-[var(--color-text-primary)] truncate">{target.name}</h2>
			<button
				class="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-3)]"
				onclick={onClose}
				aria-label="Close detail"
				title="Close">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>
		</div>
	</div>

	<!-- Body -->
	<div class="flex-1 overflow-auto p-4 space-y-4">
		<!-- Icon + Type -->
		<div class="flex flex-col items-center text-center py-4">
			<span class="text-4xl">{typeEmoji}</span>
			<p class="mt-2 text-xs text-[var(--color-text-muted)] uppercase tracking-wider">{target.type}</p>
			<code class="mt-1 px-2 py-0.5 rounded text-xs font-mono bg-[var(--color-bg-0)] text-[var(--color-text-secondary)]">{target.id}</code>
		</div>

		<!-- Status -->
		<div class="flex items-center justify-center">
			<StatusBadge status={target.status} />
		</div>

		<!-- Stats Grid -->
		<div class="grid grid-cols-3 gap-2">
			<div class="flex flex-col items-center p-2 rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border)]">
				<span class="text-sm font-semibold text-[var(--color-text-primary)]">{target.recordCount ?? 0}</span>
				<span class="text-[10px] text-[var(--color-text-muted)] uppercase">Records</span>
			</div>
			<div class="flex flex-col items-center p-2 rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border)]">
				<span class="text-sm font-semibold text-[var(--color-text-primary)]">{target.taskCount ?? 0}</span>
				<span class="text-[10px] text-[var(--color-text-muted)] uppercase">Tasks</span>
			</div>
			<div class="flex flex-col items-center p-2 rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border)]">
				<span class="text-sm">{statusEmoji}</span>
				<span class="text-[10px] text-[var(--color-text-muted)] uppercase">Status</span>
			</div>
		</div>

		<!-- Tags -->
		{#if target.tags && target.tags.length > 0}
			<div>
				<h4 class="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Tags</h4>
				<div class="flex flex-wrap gap-1.5">
					{#each target.tags as tag}
						<span class="px-2 py-0.5 rounded text-xs bg-[var(--color-bg-3)] text-[var(--color-text-secondary)]">{tag}</span>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Metadata -->
		<div>
			<h4 class="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Metadata</h4>
			<dl class="space-y-2">
				{#if target.lastSeen}
					<div class="flex justify-between text-xs">
						<dt class="text-[var(--color-text-muted)]">Last seen</dt>
						<dd class="text-[var(--color-text-secondary)] font-mono">{target.lastSeen}</dd>
					</div>
				{/if}
				{#if target.createdAt}
					<div class="flex justify-between text-xs">
						<dt class="text-[var(--color-text-muted)]">Created</dt>
						<dd class="text-[var(--color-text-secondary)] font-mono">{target.createdAt}</dd>
					</div>
				{/if}
				{#if target.updatedAt}
					<div class="flex justify-between text-xs">
						<dt class="text-[var(--color-text-muted)]">Updated</dt>
						<dd class="text-[var(--color-text-secondary)] font-mono">{target.updatedAt}</dd>
					</div>
				{/if}
			</dl>
		</div>
	</div>
</div>
