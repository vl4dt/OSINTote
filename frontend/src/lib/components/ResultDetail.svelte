<script lang="ts">
	let { result, onClose }: {
		result: { id: string; taskId: string; type: string; severity: string; message: string; target: string; timestamp: string; data: Record<string, unknown> };
		onClose: () => void;
	} = $props();

	const typeIcon = $derived(
		result.type === 'port-open' ? '🔌' :
		result.type === 'dns-record' ? '🌐' :
		result.type === 'http-response' ? '🌍' :
		result.type === 'whois' ? '📋' :
		result.type === 'subdomain' ? '🔎' :
		result.type === 'cert' ? '🔒' :
		result.type === 'vuln' ? '🛡️' :
		result.type === 'ip-lookup' ? '💻' :
		result.type === 'email-lookup' ? '📧' :
		'📊'
	);

	const severityClass = $derived(
		result.severity === 'critical' ? 'text-[var(--color-error)]' :
		result.severity === 'high' ? 'text-[var(--color-warning)]' :
		result.severity === 'warning' ? 'text-[var(--color-warning)]' :
		'text-[var(--color-info)]'
	);

	const severityBg = $derived(
		result.severity === 'critical' ? 'bg-[color:rgba(248,81,73,0.15)]' :
		result.severity === 'high' || result.severity === 'warning' ? 'bg-[color:rgba(210,153,34,0.15)]' :
		'bg-[color:rgba(88,166,255,0.15)]'
	);

	function formatData(data: Record<string, unknown>): string {
		return JSON.stringify(data, null, 2);
	}
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<span class="text-lg">{typeIcon}</span>
				<h2 class="text-sm font-semibold text-[var(--color-text-primary)] truncate">{result.type}</h2>
			</div>
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
		<!-- Severity -->
		<div class="flex items-center justify-center">
			<span class="inline-flex items-center px-3 py-1 rounded text-sm font-semibold {severityBg} {severityClass}">
				{result.severity.toUpperCase()}
			</span>
		</div>

		<!-- Message -->
		<div class="rounded-md bg-[var(--color-bg-0)] border border-[var(--color-border)] p-3">
			<p class="text-sm text-[var(--color-text-primary)] font-mono">{result.message}</p>
		</div>

		<!-- Metadata -->
		<div>
			<h4 class="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Metadata</h4>
			<dl class="space-y-2">
				<div class="flex justify-between text-xs">
					<dt class="text-[var(--color-text-muted)]">ID</dt>
					<dd class="text-[var(--color-text-secondary)] font-mono">{result.id}</dd>
				</div>
				<div class="flex justify-between text-xs">
					<dt class="text-[var(--color-text-muted)]">Task</dt>
					<dd class="text-[var(--color-text-secondary)] font-mono">{result.taskId}</dd>
				</div>
				<div class="flex justify-between text-xs">
					<dt class="text-[var(--color-text-muted)]">Target</dt>
					<dd class="text-[var(--color-text-secondary)] font-mono">{result.target}</dd>
				</div>
				<div class="flex justify-between text-xs">
					<dt class="text-[var(--color-text-muted)]">Timestamp</dt>
					<dd class="text-[var(--color-text-secondary)] font-mono">{result.timestamp}</dd>
				</div>
			</dl>
		</div>

		<!-- Raw Data -->
		{#if result.data && Object.keys(result.data).length > 0}
			<div>
				<h4 class="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Data</h4>
				<div class="rounded-md bg-[var(--color-bg-0)] border border-[var(--color-border)] p-3 overflow-auto">
					<pre class="text-xs text-[var(--color-text-secondary)] font-mono whitespace-pre-wrap">{formatData(result.data)}</pre>
				</div>
			</div>
		{/if}
	</div>
</div>
