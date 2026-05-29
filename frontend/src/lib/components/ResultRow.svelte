<script lang="ts">
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let { result, selected, onToggle }: {
		result: { id: string; taskId: string; type: string; severity: string; message: string; target: string; timestamp: string; data: Record<string, unknown> };
		selected: boolean;
		onToggle: (e: MouseEvent) => void;
	} = $props();

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

	const rowClass = $derived(
		selected
			? 'border-[var(--color-accent)] bg-[color:rgba(88,166,255,0.08)]'
			: 'border-[var(--color-border-0)] hover:border-[var(--color-border-1)] hover:bg-[var(--color-bg-3)]'
	);
</script>

<button
	class="w-full text-left p-2.5 rounded-md border transition-all {rowClass}"
	onclick={onToggle}>
	<div class="flex items-start gap-3">
		<!-- Icon -->
		<span class="text-lg shrink-0 mt-0.5">{typeIcon}</span>

		<!-- Content -->
		<div class="flex-1 min-w-0">
			<!-- Header row -->
			<div class="flex items-center gap-2 mb-0.5">
				<span class="text-xs font-mono text-[var(--color-text-3)]">{result.id}</span>
				<span class="text-[var(--color-text-3)]">•</span>
				<span class="text-xs text-[var(--color-text-2)] truncate">{result.target}</span>
				<span class="shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium {severityBg} {severityClass}">
					{result.severity}
				</span>
			</div>

			<!-- Message -->
			<p class="text-sm text-[var(--color-text-1)] font-mono truncate">{result.message}</p>

			<!-- Footer -->
			<div class="flex items-center gap-2 mt-1 text-xs">
				<code class="text-[var(--color-text-3)]">task:{result.taskId}</code>
				<span class="text-[var(--color-text-3)]">{result.timestamp}</span>
			</div>
		</div>

		<!-- Expand indicator -->
		<span class="shrink-0 text-[var(--color-text-muted)] mt-1">
			<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
				<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
			</svg>
		</span>
	</div>
</button>
