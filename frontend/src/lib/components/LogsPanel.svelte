<!-- SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com> -->
<!-- SPDX-License-Identifier: MIT -->
<!-- Logs Panel — SSE log stream with severity coloring, filtering, and export -->

<script lang="ts">
	import { browser } from '$app/environment';
	import type { LogEntry } from '$lib/types';
	import { onMount, onDestroy } from 'svelte';

	const { collapsible = false } = $props();
	let collapsed: boolean = $state(false);

	let logs: LogEntry[] = $state([]);
	let autoScroll: boolean = $state(true);
	let searching: boolean = $state(false);
	let searchQuery: string = $state('');
	let filterLevel: string = $state('');
	let filterLogger: string = $state('');

	let eventSource: EventSource | null = null;
	let connected: boolean = $state(false);
	let lastEntry: HTMLElement | null = null;

	const SEVERITY_COLORS: Record<string, string> = {
		DEBUG: '#6e7681',
		INFO: '#58a6ff',
		WARNING: '#d29922',
		ERROR: '#f85149',
		CRITICAL: '#da3633',
	};

	function getSeverityColor(level: string): string {
		return SEVERITY_COLORS[level] ?? SEVERITY_COLORS.INFO;
	}

	function connectSSE(): void {
		if (!browser) return;

		const params = new URLSearchParams();
		if (filterLevel) params.set('level', filterLevel);
		if (filterLogger) params.set('logger_name', filterLogger);
		const query = params.toString();
		const url = `/api/logs/stream${query ? '?' + query : ''}`;

		eventSource = new EventSource(url);
		connected = true;

		eventSource.onmessage = (event: MessageEvent) => {
			try {
				const entry: LogEntry = JSON.parse(event.data);
				logs = [...logs, entry];
				if (autoScroll) {
					scrollToBottom();
				}
			} catch {
				// Ignore non-JSON messages (ping/keep-alive)
			}
		};

		eventSource.onerror = () => {
			connected = false;
			eventSource?.close();
		};
	}

	function scrollToBottom(): void {
		if (lastEntry) {
			setTimeout(() => lastEntry?.scrollIntoView({ block: 'end' }), 50);
		}
	}

	function clearLogs(): void {
		logs = [];
	}

	function exportLogs(): void {
		const json = JSON.stringify(logs, null, 2);
		const blob = new Blob([json], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `osintote-logs-${new Date().toISOString().slice(0, 10)}.json`;
		a.click();
		URL.revokeObjectURL(url);
	}

	let filteredLogs = $derived(
		logs.filter((log) => {
			const matchesLevel = !filterLevel || log.level === filterLevel;
			const matchesLogger = !filterLogger || log.logger.includes(filterLogger);
			const matchesSearch = !searchQuery ||
				log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
				log.logger.toLowerCase().includes(searchQuery.toLowerCase());
			return matchesLevel && matchesLogger && matchesSearch;
		})
	);

	onMount(() => {
		if (browser) {
			connectSSE();
		}
	});

	onDestroy(() => {
		eventSource?.close();
	});
</script>

<div class="logs-panel">
	{#if collapsible}
		<button
			class="logs-header"
			onclick={() => (collapsed = !collapsed)}
		>
			<span>Logs</span>
			<span class="log-count">{logs.length}</span>
			<span class="log-status connected:visible">{connected ? '●' : '○'}</span>
			<span class="collapse-arrow">{collapsed ? '▼' : '▲'}</span>
		</button>
	{/if}

	<div class="logs-body" class:collapsed>
		<!-- Filter bar -->
		<div class="filter-bar">
			<input
				type="text"
				placeholder="Search logs..."
				class="search-input"
				bind:value={searchQuery}
				onfocus={() => (searching = true)}
				onblur={() => (searching = false)}
			/>
			<select class="filter-select" bind:value={filterLevel}>
				<option value="">All Levels</option>
				<option value="DEBUG">DEBUG</option>
				<option value="INFO">INFO</option>
				<option value="WARNING">WARNING</option>
				<option value="ERROR">ERROR</option>
				<option value="CRITICAL">CRITICAL</option>
			</select>
			<input
				type="text"
				placeholder="Logger name..."
				class="filter-input"
				bind:value={filterLogger}
			/>
		</div>

		<!-- Action bar -->
		<div class="action-bar">
			<label class="auto-scroll-toggle">
				<input type="checkbox" bind:checked={autoScroll} />
				Auto-scroll
			</label>
			<button class="btn btn-sm btn-secondary" onclick={clearLogs}>
				Clear
			</button>
			<button class="btn btn-sm btn-secondary" onclick={exportLogs}>
				Export
			</button>
			<span class="status-dot connected:visible">{connected ? '●' : '○'}</span>
		</div>

		<!-- Log entries -->
		<div class="log-entries">
			{#each filteredLogs as log (log.timestamp + log.message)}
				<div class="log-entry" bind:this={lastEntry}>
					<span class="log-timestamp">{log.timestamp}</span>
					<span
						class="log-level"
						style="color: {getSeverityColor(log.level)}"
					>
						{log.level}
					</span>
					<span class="log-logger">{log.logger}</span>
					<span class="log-message">{log.message}</span>
				</div>
			{:else}
				<div class="empty-state">
					{#if logs.length === 0}
						<span>Waiting for logs...</span>
					{:else}
						<span>No logs match the current filters.</span>
					{/if}
				</div>
			{/each}
		</div>
	</div>
</div>

<style>
	.logs-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.logs-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: var(--color-bg-subtle);
		border-bottom: 1px solid var(--color-border-default);
		cursor: pointer;
		user-select: none;
	}

	.logs-header:hover {
		background: var(--color-bg-inset);
	}

	.log-count {
		background: var(--color-accent);
		color: var(--color-text-on-emphasis);
		border-radius: 9999px;
		padding: 0.125rem 0.5rem;
		font-size: 0.75rem;
	}

	.log-status {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		display: none;
	}

	.connected .log-status,
	.connected .status-dot {
		display: inline;
	}

	.collapse-arrow {
		margin-left: auto;
		transition: transform 0.2s;
	}

	.logs-body {
		display: flex;
		flex-direction: column;
		overflow: hidden;
		transition: max-height 0.3s ease;
	}

	.logs-body.collapsed {
		max-height: 0;
		overflow: hidden;
	}

	.filter-bar {
		display: flex;
		gap: 0.5rem;
		padding: 0.5rem;
		background: var(--color-bg-subtle);
		border-bottom: 1px solid var(--color-border-default);
	}

	.search-input {
		flex: 1;
		padding: 0.25rem 0.5rem;
		background: var(--color-canvas-subtle);
		border: 1px solid var(--color-border-default);
		border-radius: 4px;
		color: var(--color-text);
		font-size: 0.875rem;
	}

	.filter-select,
	.filter-input {
		padding: 0.25rem 0.5rem;
		background: var(--color-canvas-subtle);
		border: 1px solid var(--color-border-default);
		border-radius: 4px;
		color: var(--color-text);
		font-size: 0.875rem;
	}

	.action-bar {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.25rem 0.5rem;
		border-bottom: 1px solid var(--color-border-default);
	}

	.auto-scroll-toggle {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: var(--color-text-muted);
		cursor: pointer;
	}

	.btn-sm {
		padding: 0.125rem 0.5rem;
		font-size: 0.75rem;
		border: 1px solid var(--color-border-default);
		border-radius: 4px;
		background: var(--color-btn-primary-bg);
		color: var(--color-btn-primary-text);
		cursor: pointer;
	}

	.btn-secondary {
		background: var(--color-bg-subtle);
		color: var(--color-text);
	}

	.status-dot {
		margin-left: auto;
		font-size: 0.75rem;
		color: var(--color-text-muted);
		display: none;
	}

	.connected .status-dot {
		display: inline;
	}

	.log-entries {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.8125rem;
	}

	.log-entry {
		display: flex;
		gap: 0.75rem;
		padding: 0.25rem 0;
		border-bottom: 1px solid var(--color-border-subtle);
	}

	.log-entry:hover {
		background: var(--color-bg-inset);
	}

	.log-timestamp {
		color: var(--color-text-muted);
		min-width: 180px;
		flex-shrink: 0;
	}

	.log-level {
		min-width: 60px;
		font-weight: 600;
		flex-shrink: 0;
	}

	.log-logger {
		color: var(--color-text-muted);
		min-width: 120px;
		flex-shrink: 0;
	}

	.log-message {
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.empty-state {
		text-align: center;
		color: var(--color-text-muted);
		padding: 2rem;
	}
</style>
