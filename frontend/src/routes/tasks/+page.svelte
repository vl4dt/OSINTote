<script lang="ts">
	import TaskCard from '$lib/components/TaskCard.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	// Placeholder data for the UI shell
	let tasks = $state([
		{
			id: 'tsk-001',
			name: 'Port scan: example.com',
			type: 'nmap',
			status: 'running',
			targetId: 'tgt-001',
			createdAt: '2026-05-28 14:30',
			progress: 65
		},
		{
			id: 'tsk-002',
			name: 'DNS enumeration: api.service.dev',
			type: 'dns-enumerate',
			status: 'completed',
			targetId: 'tgt-002',
			createdAt: '2026-05-28 12:10',
			progress: 100
		},
		{
			id: 'tsk-003',
			name: 'Subdomain brute force: internal.net',
			type: 'subdomain',
			status: 'failed',
			targetId: 'tgt-003',
			createdAt: '2026-05-27 09:40',
			progress: 34
		},
		{
			id: 'tsk-004',
			name: 'WHOIS lookup: malicious-domain.xyz',
			type: 'whois',
			status: 'completed',
			targetId: 'tgt-004',
			createdAt: '2026-05-25 18:15',
			progress: 100
		},
		{
			id: 'tsk-005',
			name: 'Certificate scan: example.com',
			type: 'cert-scan',
			status: 'pending',
			targetId: 'tgt-001',
			createdAt: '2026-05-28 15:00',
			progress: 0
		}
	]);

	let selectedId = $state<string | null>(null);

	function handleTaskClick(taskId: string) {
		selectedId = taskId;
	}
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Tasks Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border-0)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-lg font-semibold text-[var(--color-text-0)]">Tasks</h1>
				<p class="text-xs text-[var(--color-text-2)] mt-0.5">{tasks.length} tasks</p>
			</div>
			<div class="flex items-center gap-2">
				<!-- Filter -->
				<select class="px-2 py-1 text-xs rounded border border-[var(--color-border-0)] bg-[var(--color-bg-2)] text-[var(--color-text-1)] focus:outline-none focus:border-[var(--color-accent)] transition-colors">
					<option value="all">All</option>
					<option value="running">Running</option>
					<option value="completed">Completed</option>
					<option value="failed">Failed</option>
					<option value="pending">Pending</option>
				</select>

				<!-- Create button -->
				<button class="px-2.5 py-1 text-xs font-medium rounded-md bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] transition-colors">
					+ New Task
				</button>
			</div>
		</div>
	</div>

	<!-- Tasks List -->
	<div class="flex-1 overflow-auto p-2 space-y-1">
		{#each tasks as task (task.id)}
			<TaskCard
				{task}
				selected={selectedId === task.id}
				on:click={() => handleTaskClick(task.id)} />
		{/each}
	</div>

	<!-- Bottom Bar -->
	<div class="flex items-center justify-between px-3 py-2 border-t border-[var(--color-border-0)] bg-[var(--color-bg-2)] text-xs text-[var(--color-text-3)]">
		<div class="flex items-center gap-2">
			<span>{tasks.filter(t => t.status === 'running').length} running</span>
			<span>|</span>
			<span>{tasks.filter(t => t.status === 'completed').length} completed</span>
			<span>|</span>
			<span>{tasks.filter(t => t.status === 'failed').length} failed</span>
		</div>
		<div class="flex items-center gap-2">
			<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-1)] transition-colors">
				Clear Completed
			</button>
			<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-1)] transition-colors">
				Export
			</button>
		</div>
	</div>
</div>
