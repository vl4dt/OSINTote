<script lang="ts">
	import { onMount } from 'svelte';
	import { apiService } from '$lib/api/mock';
	import EmptyState from '$lib/components/EmptyState.svelte';

	let targets = $state<number>(0);
	let tasks = $state<number>(0);
	let runningTasks = $state<number>(0);
	let results = $state<number>(0);
	let criticalAlerts = $state<number>(0);
	let loading = $state(true);

	const stats = $derived([
		{
			label: 'Targets',
			value: targets,
			icon: '🎯',
			color: 'text-[var(--color-accent)]',
			href: '/targets'
		},
		{
			label: 'Tasks',
			value: tasks,
			icon: '⚡',
			color: 'text-[var(--color-info)]',
			href: '/tasks'
		},
		{
			label: 'Running',
			value: runningTasks,
			icon: '🔄',
			color: 'text-[var(--color-warning)]',
			href: '/tasks?status=running'
		},
		{
			label: 'Results',
			value: results,
			icon: '📊',
			color: 'text-[var(--color-success)]',
			href: '/results'
		},
		{
			label: 'Critical',
			value: criticalAlerts,
			icon: '🚨',
			color: 'text-[var(--color-error)]',
			href: '/results?severity=critical'
		},
		{
			label: 'Uptime',
			value: '99.9%',
			icon: '💚',
			color: 'text-[var(--color-success)]',
			href: '/settings'
		}
	]);

	onMount(async () => {
		try {
			const [tCount, tList, rCount] = await Promise.all([
				apiService.getTargets().then(t => t.length),
				apiService.getTasks().then(t => {
					runningTasks = t.filter(x => x.status === 'running').length;
					return t.length;
				}),
				apiService.getResults().then(r => {
					criticalAlerts = r.filter(x => x.severity === 'critical').length;
					return r.length;
				})
			]);
			targets = tCount;
			tasks = tList;
			results = rCount;
		} finally {
			loading = false;
		}
	});
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<h1 class="text-2xl font-bold text-[var(--color-text-primary)]">Dashboard</h1>
		<p class="text-sm text-[var(--color-text-secondary)] mt-1">OSINT reconnaissance overview</p>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-auto p-6">
		{#if loading}
			<div class="flex items-center justify-center h-full">
				<div class="flex flex-col items-center gap-3">
					<div class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
					<span class="text-sm text-[var(--color-text-muted)]">Loading dashboard...</span>
				</div>
			</div>
		{:else}
			<!-- Stats Grid -->
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
				{#each stats as stat}
					<a
						href={stat.href}
						class="flex items-center gap-4 p-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-1)] hover:border-[var(--color-border-light)] hover:bg-[var(--color-bg-2)] transition-all group">
						<span class="text-2xl group-hover:scale-110 transition-transform">{stat.icon}</span>
						<div>
							<p class="text-2xl font-bold {stat.color}">{stat.value}</p>
							<p class="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">{stat.label}</p>
						</div>
					</a>
				{/each}
			</div>

			<!-- Quick Actions -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<!-- Recent Tasks -->
				<div class="p-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-1)]">
					<h3 class="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Recent Tasks</h3>
					<div class="space-y-2">
						<div class="flex items-center justify-between text-sm">
							<span class="text-[var(--color-text-secondary)]">Port scan: example.com</span>
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[color:rgba(88,166,255,0.15)] text-[var(--color-info)]">running</span>
						</div>
						<div class="flex items-center justify-between text-sm">
							<span class="text-[var(--color-text-secondary)]">DNS enumeration: api.service.dev</span>
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[color:rgba(63,185,80,0.15)] text-[var(--color-success)]">completed</span>
						</div>
						<div class="flex items-center justify-between text-sm">
							<span class="text-[var(--color-text-secondary)]">Subdomain brute force: internal.net</span>
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[color:rgba(248,81,73,0.15)] text-[var(--color-error)]">failed</span>
						</div>
					</div>
					<a href="/tasks" class="block mt-3 text-xs text-[var(--color-accent)] hover:underline">View all →</a>
				</div>

				<!-- Critical Findings -->
				<div class="p-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-1)]">
					<h3 class="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Critical Findings</h3>
					{#if criticalAlerts > 0}
						<div class="space-y-2">
							<div class="flex items-start gap-2 p-2 rounded bg-[color:rgba(248,81,73,0.1)] border border-[color:rgba(248,81,73,0.3)]">
								<span class="text-sm">🛡️</span>
								<span class="text-xs text-[var(--color-text-secondary)]">CVE-2025-1234: RCE in Apache Log4j</span>
							</div>
							<div class="flex items-start gap-2 p-2 rounded bg-[color:rgba(248,81,73,0.1)] border border-[color:rgba(248,81,73,0.3)]">
								<span class="text-sm">🔒</span>
								<span class="text-xs text-[var(--color-text-secondary)]">Open SSH on production server</span>
							</div>
						</div>
					{:else}
						<div class="flex flex-col items-center justify-center py-6 text-center">
							<span class="text-2xl mb-2">✅</span>
							<p class="text-sm text-[var(--color-text-muted)]">No critical findings</p>
						</div>
					{/if}
					<a href="/results" class="block mt-3 text-xs text-[var(--color-accent)] hover:underline">View all results →</a>
				</div>
			</div>
		{/if}
	</div>
</div>
