<script lang="ts">
	export let task: {
		id: string;
		name: string;
		type: string;
		status?: string;
		targetId?: string;
		createdAt?: string;
		progress?: number;
	};

	export let selected: boolean = false;
	export let onClick: () => void = () => {};
</script>

<button
	class="w-full text-left p-3 rounded-md border transition-all
		{selected
			? 'border-[var(--color-accent)] bg-[color:rgba(88,166,255,0.08)] shadow-sm'
			: 'border-[var(--color-border-0)] bg-[var(--color-bg-2)] hover:border-[var(--color-border-1)] hover:bg-[var(--color-bg-3)]'}"
	on:click>
	<div class="flex items-start justify-between gap-2 mb-1.5">
		<span class="text-sm font-medium text-[var(--color-text-0)] truncate flex-1">
			{task.name}
		</span>
		{#if task.status}
			<span class="shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium
				{task.status === 'running' ? 'bg-[color:rgba(88,166,255,0.15)] text-[var(--color-info)]' :
				 task.status === 'completed' ? 'bg-[color:rgba(63,185,80,0.15)] text-[var(--color-success)]' :
				 task.status === 'failed' ? 'bg-[color:rgba(248,81,73,0.15)] text-[var(--color-error)]' :
				 'bg-[var(--color-bg-3)] text-[var(--color-text-2)]'}">
				{task.status}
			</span>
		{/if}
	</div>

	<div class="flex items-center gap-1.5 text-xs text-[var(--color-text-2)]">
		<span>Type: <code class="text-[var(--color-text-3)]">{task.type}</code></span>
		{#if task.targetId}
			<span class="text-[var(--color-text-3)]">|</span>
			<span>Target: <code class="text-[var(--color-text-3)]">{task.targetId}</code></span>
		{/if}
	</div>

	{#if task.progress !== undefined}
		<div class="mt-2 w-full h-1 bg-[var(--color-bg-0)] rounded-full overflow-hidden">
			<div
				class="h-full bg-[var(--color-accent)] rounded-full transition-all duration-300"
				style="width: {task.progress}%"></div>
		</div>
	{/if}

	{#if task.createdAt}
		<div class="mt-1 text-xs text-[var(--color-text-3)]">
			Created: {task.createdAt}
		</div>
	{/if}
</button>
