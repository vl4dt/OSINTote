<script lang="ts">
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let { task, onClose }: {
		task: { id: string; name: string; type: string; status: string; targetId?: string; createdAt: string; updatedAt: string; startedAt?: string; completedAt?: string; progress: number; recordsCount: number; error?: string; recipeId?: string };
		onClose: () => void;
	} = $props();

	const typeIcon = $derived(
		task.type === 'nmap' ? '🔍' :
		task.type === 'dns-enumerate' ? '🌐' :
		task.type === 'whois' ? '📋' :
		task.type === 'http-probe' ? '🌍' :
		task.type === 'subdomain' ? '🔎' :
		task.type === 'cert-scan' ? '🔒' :
		task.type === 'vuln-scan' ? '🛡️' :
		task.type === 'api-scan' ? '🔌' :
		'⚡'
	);

	const durationText = $derived(
		task.startedAt && task.completedAt
			? calculateDuration(task.startedAt, task.completedAt)
			: task.startedAt
				? `Running since ${task.startedAt}`
				: 'Not started'
	);

	function calculateDuration(start: string, end: string): string {
		const s = new Date(start.replace(' ', 'T')).getTime();
		const e = new Date(end.replace(' ', 'T')).getTime();
		const diff = e - s;
		if (diff < 60000) return `${Math.floor(diff / 1000)}s`;
		if (diff < 3600000) return `${Math.floor(diff / 60000)}m ${Math.floor((diff % 60000) / 1000)}s`;
		return `${Math.floor(diff / 3600000)}h ${Math.floor((diff % 3600000) / 60000)}m`;
	}

	function copyError(): void {
		if (task.error) {
			navigator.clipboard?.writeText(task.error);
		}
	}
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between">
			<h2 class="text-sm font-semibold text-[var(--color-text-primary)] truncate">{task.name}</h2>
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
		<!-- Type + Status -->
		<div class="flex flex-col items-center text-center py-3">
			<span class="text-3xl">{typeIcon}</span>
			<p class="mt-1 text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-mono">{task.type}</p>
			<div class="mt-2">
				<StatusBadge status={task.status} />
			</div>
		</div>

		<!-- Progress Bar -->
		{#if task.status === 'running'}
			<div>
				<div class="flex justify-between text-xs text-[var(--color-text-muted)] mb-1">
					<span>Progress</span>
					<span class="font-mono">{task.progress}%</span>
				</div>
				<div class="w-full h-2 bg-[var(--color-bg-0)] rounded-full overflow-hidden">
					<div
						class="h-full bg-[var(--color-accent)] rounded-full transition-all duration-500"
						style="width: {task.progress}%"></div>
				</div>
			</div>
		{/if}

		<!-- Stats Grid -->
		<div class="grid grid-cols-3 gap-2">
			<div class="flex flex-col items-center p-2 rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border)]">
				<span class="text-sm font-semibold text-[var(--color-text-primary)]">{task.recordsCount}</span>
				<span class="text-[10px] text-[var(--color-text-muted)] uppercase">Records</span>
			</div>
			<div class="flex flex-col items-center p-2 rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border)]">
				<span class="text-sm font-semibold text-[var(--color-text-primary)]">{task.progress}%</span>
				<span class="text-[10px] text-[var(--color-text-muted)] uppercase">Progress</span>
			</div>
			<div class="flex flex-col items-center p-2 rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border)]">
				<span class="text-[10px] text-[var(--color-text-muted)] uppercase">Duration</span>
				<span class="text-xs text-[var(--color-text-secondary)] font-mono mt-0.5">{durationText}</span>
			</div>
		</div>

		<!-- Error -->
		{#if task.error}
			<div class="rounded-md bg-[color:rgba(248,81,73,0.1)] border border-[color:rgba(248,81,73,0.3)] p-3">
				<div class="flex items-start justify-between gap-2">
					<div class="flex-1">
						<h4 class="text-xs font-semibold text-[var(--color-error)] mb-1">Error</h4>
						<p class="text-xs text-[var(--color-text-secondary)] font-mono break-all">{task.error}</p>
					</div>
					<button
						class="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] p-1"
						onclick={copyError}
						title="Copy error"
						aria-label="Copy error to clipboard">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
							<path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
							<path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 1 1 0 000 2H6V3z" />
						</svg>
					</button>
				</div>
			</div>
		{/if}

		<!-- Recipe -->
		{#if task.recipeId}
			<div class="text-xs">
				<dt class="text-[var(--color-text-muted)]">Recipe</dt>
				<dd class="text-[var(--color-text-secondary)] font-mono">{task.recipeId}</dd>
			</div>
		{/if}

		<!-- Target -->
		{#if task.targetId}
			<div>
				<dt class="text-[var(--color-text-muted)]">Target</dt>
				<dd class="text-[var(--color-text-secondary)] font-mono">{task.targetId}</dd>
			</div>
		{/if}

		<!-- Timestamps -->
		<div>
			<h4 class="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Timeline</h4>
			<dl class="space-y-1.5">
				{#if task.createdAt}
					<div class="flex justify-between text-xs">
						<dt class="text-[var(--color-text-muted)]">Created</dt>
						<dd class="text-[var(--color-text-secondary)] font-mono">{task.createdAt}</dd>
					</div>
				{/if}
				{#if task.startedAt}
					<div class="flex justify-between text-xs">
						<dt class="text-[var(--color-text-muted)]">Started</dt>
						<dd class="text-[var(--color-text-secondary)] font-mono">{task.startedAt}</dd>
					</div>
				{/if}
				{#if task.completedAt}
					<div class="flex justify-between text-xs">
						<dt class="text-[var(--color-text-muted)]">Completed</dt>
						<dd class="text-[var(--color-text-secondary)] font-mono">{task.completedAt}</dd>
					</div>
				{/if}
			</dl>
		</div>
	</div>
</div>
