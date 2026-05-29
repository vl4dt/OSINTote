<script lang="ts">
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	// Placeholder data for the UI shell
	let results = $state([
		{
			id: 'res-001',
			taskId: 'tsk-001',
			type: 'port-open',
			severity: 'info',
			message: 'Port 80/tcp OPEN (HTTP)',
			target: 'example.com',
			timestamp: '2026-05-28 14:32:15',
			data: { port: 80, protocol: 'tcp', service: 'http', version: 'nginx/1.24.0' }
		},
		{
			id: 'res-002',
			taskId: 'tsk-001',
			type: 'port-open',
			severity: 'warning',
			message: 'Port 443/tcp OPEN (HTTPS)',
			target: 'example.com',
			timestamp: '2026-05-28 14:32:16',
			data: { port: 443, protocol: 'tcp', service: 'https', version: 'nginx/1.24.0' }
		},
		{
			id: 'res-003',
			taskId: 'tsk-001',
			type: 'port-open',
			severity: 'critical',
			message: 'Port 22/tcp OPEN (SSH)',
			target: 'example.com',
			timestamp: '2026-05-28 14:32:17',
			data: { port: 22, protocol: 'tcp', service: 'ssh', version: 'OpenSSH_9.2p1' }
		},
		{
			id: 'res-004',
			taskId: 'tsk-002',
			type: 'dns-record',
			severity: 'info',
			message: 'A record: api.service.dev → 10.0.0.50',
			target: 'api.service.dev',
			timestamp: '2026-05-28 12:15:30',
			data: { recordType: 'A', value: '10.0.0.50', ttl: 3600 }
		},
		{
			id: 'res-005',
			taskId: 'tsk-002',
			type: 'dns-record',
			severity: 'info',
			message: 'MX record: api.service.dev → mail.service.dev',
			target: 'api.service.dev',
			timestamp: '2026-05-28 12:15:31',
			data: { recordType: 'MX', value: 'mail.service.dev', priority: 10 }
		}
	]);

	let selectedResult = $state<typeof results[0] | null>(null);

	function handleResultClick(result: typeof results[0]) {
		selectedResult = result;
	}
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Results Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border-0)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-lg font-semibold text-[var(--color-text-0)]">Results</h1>
				<p class="text-xs text-[var(--color-text-2)] mt-0.5">{results.length} findings</p>
			</div>
			<div class="flex items-center gap-2">
				<select class="px-2 py-1 text-xs rounded border border-[var(--color-border-0)] bg-[var(--color-bg-2)] text-[var(--color-text-1)] focus:outline-none focus:border-[var(--color-accent)] transition-colors">
					<option value="all">All Severities</option>
					<option value="critical">Critical</option>
					<option value="warning">Warning</option>
					<option value="info">Info</option>
				</select>
				<button class="px-2.5 py-1 text-xs font-medium rounded-md bg-[var(--color-bg-2)] border border-[var(--color-border-0)] text-[var(--color-text-1)] hover:bg-[var(--color-bg-3)] transition-colors">
					Export JSON
				</button>
			</div>
		</div>
	</div>

	<!-- Results List -->
	<div class="flex-1 overflow-auto p-2 space-y-1">
		{#each results as result (result.id)}
			<button
				class="w-full text-left p-2.5 rounded-md border transition-all
					{selectedResult?.id === result.id
						? 'border-[var(--color-accent)] bg-[color:rgba(88,166,255,0.08)]'
						: 'border-[var(--color-border-0)] bg-[var(--color-bg-2)] hover:border-[var(--color-border-1)] hover:bg-[var(--color-bg-3)]'}"
				onclick={() => handleResultClick(result)}>
				<div class="flex items-start justify-between gap-2">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-0.5">
							<span class="text-xs font-mono text-[var(--color-text-3)]">{result.id}</span>
							<span class="text-[var(--color-text-3)]">•</span>
							<span class="text-xs text-[var(--color-text-2)]">{result.target}</span>
						</div>
						<p class="text-sm text-[var(--color-text-1)] truncate">{result.message}</p>
						<div class="flex items-center gap-2 mt-1">
							<code class="text-xs text-[var(--color-text-3)]">{result.taskId}</code>
							<span class="text-xs text-[var(--color-text-3)]">{result.timestamp}</span>
						</div>
					</div>
					<span class="shrink-0 text-xs font-medium
						{result.severity === 'critical' ? 'text-[var(--color-error)]' :
						 result.severity === 'warning' ? 'text-[var(--color-warning)]' :
						 'text-[var(--color-info)]'}">
						{result.severity}
					</span>
				</div>
			</button>
		{/each}
	</div>
</div>
