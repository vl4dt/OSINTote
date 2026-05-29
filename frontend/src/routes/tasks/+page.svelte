<script lang="ts">
	import { onMount } from 'svelte';
	import type { Task, SSEEvent } from '$lib/types';
	import { apiService } from '$lib/api/real';
	import TaskCard from '$lib/components/TaskCard.svelte';
	import TaskDetail from '$lib/components/TaskDetail.svelte';
	import TaskDialog from '$lib/components/TaskDialog.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	let tasks = $state<Task[]>([]);
	let filteredTasks = $state<Task[]>([]);
	let selectedId = $state<string | null>(null);
	let detailTask = $state<Task | null>(null);
	let showCreateDialog = $state(false);
	let loading = $state(true);

	let statusFilter = $state<string>('all');

	async function loadTasks(): Promise<void> {
		loading = true;
		try {
			tasks = await apiService.getTasks();
		} finally {
			loading = false;
			applyFilters();
		}
	}

	function applyFilters(): void {
		let result = [...tasks];

		if (statusFilter !== 'all') {
			result = result.filter(t => t.status === statusFilter);
		}

		filteredTasks = result;
	}

	function handleStatusChange(e: Event): void {
		statusFilter = (e.target as HTMLSelectElement).value;
		applyFilters();
	}

	function handleTaskClick(task: Task): void {
		selectedId = task.id;
		detailTask = task;
	}

	function handleTaskCloseDetail(): void {
		selectedId = null;
		detailTask = null;
	}

	// SSE cleanup handles
	const sseHandles = $state<Set<() => void>>(new Set());

	// SSE handler for live updates
	function handleSSEEvent(event: SSEEvent): void {
		if (event.type === 'progress' && event.taskId && event.data?.progress) {
			const task = tasks.find(t => t.id === event.taskId);
			if (task) {
				task.progress = event.data.progress as number;
				if (selectedId === task.id) {
					detailTask = { ...task };
				}
				applyFilters();
			}
		} else if (event.type === 'task_started' && event.taskId) {
			const task = tasks.find(t => t.id === event.taskId);
			if (task) {
				task.status = 'running';
				applyFilters();
			}
		} else if (event.type === 'task_finished' && event.taskId) {
			const task = tasks.find(t => t.id === event.taskId);
			if (task) {
				task.status = 'completed';
				task.progress = 100;
				task.completedAt = new Date().toISOString().replace('T', ' ').slice(0, 19);
				applyFilters();
			}
		} else if (event.type === 'task_failed' && event.taskId) {
			const task = tasks.find(t => t.id === event.taskId);
			if (task) {
				task.status = 'failed';
				applyFilters();
			}
		}
	}

	// Connect to SSE for all running tasks
	function connectSSE(): void {
		tasks.forEach(t => {
			if (t.status === 'running') {
				const handle = apiService.subscribeSSEForTask(t.id, handleSSEEvent);
				sseHandles.add(handle);
			}
		});
	}

	// Disconnect all SSE streams
	function disconnectSSE(): void {
		for (const handle of sseHandles.values()) {
			handle();
		}
		sseHandles.clear();
	}

	async function handleCreateTask(data: { name: string; type: string; targetId: string; recipeId?: string }): Promise<void> {
		await apiService.createTask({
			name: data.name,
			type: data.type as Task['type'],
			status: 'queued',
			targetId: data.targetId,
			recipeId: data.recipeId
		});
		showCreateDialog = false;
		await loadTasks();
	}

	async function handleStartTask(id: string): Promise<void> {
		const task = tasks.find(t => t.id === id);
		if (task) {
			task.status = 'running';
			task.startedAt = new Date().toISOString().replace('T', ' ').slice(0, 19);
			task.progress = Math.max(task.progress, 5);
			if (selectedId === task.id) {
				detailTask = { ...task };
			}
			applyFilters();
		}
	}

	async function handleCancelTask(id: string): Promise<void> {
		const task = tasks.find(t => t.id === id);
		if (task && task.status === 'running') {
			task.status = 'canceled';
			task.error = 'User canceled';
			task.updatedAt = new Date().toISOString().replace('T', ' ').slice(0, 19);
			if (selectedId === task.id) {
				detailTask = { ...task };
			}
			applyFilters();
		}
	}

	async function handleResumeTask(id: string): Promise<void> {
		const task = tasks.find(t => t.id === id);
		if (task && (task.status === 'failed' || task.status === 'canceled')) {
			task.status = 'running';
			task.startedAt = new Date().toISOString().replace('T', ' ').slice(0, 19);
			task.progress = Math.max(task.progress, 5);
			task.error = undefined;
			if (selectedId === task.id) {
				detailTask = { ...task };
			}
			applyFilters();
		}
	}

	function handleDeleteTask(id: string): void {
		apiService.deleteTask(id);
		tasks = tasks.filter(t => t.id !== id);
		if (selectedId === id) {
			selectedId = null;
			detailTask = null;
		}
		applyFilters();
	}

	const runningCount = $derived(tasks.filter(t => t.status === 'running').length);
	const completedCount = $derived(tasks.filter(t => t.status === 'completed').length);
	const failedCount = $derived(tasks.filter(t => t.status === 'failed').length);

	onMount(() => {
		loadTasks();
		// Connect SSE after a short delay so tasks have loaded
		setTimeout(connectSSE, 500);
	});
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between gap-2">
			<div>
				<h1 class="text-lg font-semibold text-[var(--color-text-primary)]">Tasks</h1>
				<p class="text-xs text-[var(--color-text-secondary)] mt-0.5">{tasks.length} tasks total</p>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<!-- Status Filter -->
				<select
					value={statusFilter}
					onchange={handleStatusChange}
					class="px-2 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)] transition-colors">
					<option value="all">All Status</option>
					<option value="running">Running</option>
					<option value="completed">Completed</option>
					<option value="failed">Failed</option>
					<option value="canceled">Canceled</option>
					<option value="queued">Queued</option>
					<option value="pending">Pending</option>
				</select>

				<!-- Create button -->
				<button
					class="px-2.5 py-1 text-xs font-medium rounded-md bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] transition-colors"
					onclick={() => { showCreateDialog = true; }}>
					+ New Task
				</button>
			</div>
		</div>
	</div>

	<!-- Content -->
	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<div class="flex flex-col items-center gap-2">
				<div class="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
				<span class="text-xs text-[var(--color-text-muted)]">Loading tasks...</span>
			</div>
		</div>
	{:else if filteredTasks.length === 0}
		<EmptyState
			title={statusFilter !== 'all' ? 'No matching tasks' : 'No tasks yet'}
			description={statusFilter !== 'all' ? 'Try changing the status filter' : 'Create a new task to start reconnaissance.'}
			actionLabel={!showCreateDialog && tasks.length === 0 ? 'Create Task' : undefined}
			onAction={() => { showCreateDialog = true; }} />
	{:else}
		<div class="flex-1 overflow-auto p-2 space-y-1">
			{#each filteredTasks as task (task.id)}
				<TaskCard
					{task}
					selected={selectedId === task.id}
					onClick={() => handleTaskClick(task)} />
			{/each}
		</div>
	{/if}

	<!-- Bottom Bar -->
	{#if filteredTasks.length > 0}
		<div class="flex items-center justify-between px-3 py-2 border-t border-[var(--color-border)] bg-[var(--color-bg-2)] text-xs text-[var(--color-text-muted)]">
			<div class="flex items-center gap-2">
				<span class="flex items-center gap-1">
					<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-info)]"></span>
					{runningCount} running
				</span>
				<span>|</span>
				<span class="flex items-center gap-1">
					<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-success)]"></span>
					{completedCount} done
				</span>
				<span>|</span>
				<span class="flex items-center gap-1">
					<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-error)]"></span>
					{failedCount} failed
				</span>
			</div>
			<div class="flex items-center gap-2">
				<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-primary)] transition-colors">
					Clear Completed
				</button>
				<button class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-primary)] transition-colors">
					Export
				</button>
			</div>
		</div>
	{/if}

	<!-- Task Detail Panel (right slot) -->
	{#if detailTask}
		<TaskDetail task={detailTask} onClose={handleTaskCloseDetail} />
	{/if}

	<!-- Create Task Dialog -->
	<TaskDialog
		open={showCreateDialog}
		onClose={() => { showCreateDialog = false; }}
		onSubmit={handleCreateTask} />
</div>
