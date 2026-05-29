<script lang="ts">
	import './layout.css';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { preloadAll } from '$lib/lazyRoutes';
	import { onMount } from 'svelte';

	// Pre-load all routes on mount
	onMount(() => {
		preloadAll();
	});

	// Navigation tabs
	const navTabs = [
		{ id: 'dashboard', label: 'Dashboard', href: '/dashboard' },
		{ id: 'targets', label: 'Targets', href: '/targets' },
		{ id: 'tasks', label: 'Tasks', href: '/tasks' },
		{ id: 'results', label: 'Results', href: '/results' }
	];

	// Update clock (browser only)
	let clockInterval: ReturnType<typeof setInterval> | null = null;
	
	if (browser) {
		function updateClock() {
			const el = document.getElementById('clock');
			if (el) {
				const now = new Date();
				el.textContent = now.toLocaleTimeString();
			}
		}
		updateClock();
		clockInterval = setInterval(updateClock, 1000);
	}
</script>

<svelte:head>
	<title>OSINTote — OSINT Reconnaissance Platform</title>
	<meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

<div class="flex flex-col h-screen overflow-hidden">
	<!-- Header Bar -->
	<header class="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-1)] shrink-0">
		<div class="flex items-center gap-3">
			<!-- Logo/Brand -->
			<a href="/" class="flex items-center gap-2">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-[var(--color-accent)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="12" cy="12" r="10" />
					<line x1="2" y1="12" x2="22" y2="12" />
					<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
				</svg>
				<span class="text-sm font-semibold text-[var(--color-text-primary)] tracking-wide">OSINTote</span>
			</a>

			<!-- Separator -->
			<span class="h-4 w-px bg-[var(--color-border)]" />

			<!-- Status indicator -->
			<span class="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
				<span class="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] animate-pulse" />
				Connected
			</span>
		</div>

		<div class="flex items-center gap-2">
			<!-- Search -->
			<div class="relative">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
				</svg>
				<input
					type="text"
					placeholder="Search..."
					class="w-48 pl-7 pr-3 py-1 text-sm rounded border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] transition-colors" />
			</div>
		</div>
	</header>

	<!-- Tab Navigation -->
	<nav class="flex items-center border-b border-[var(--color-border)] bg-[var(--color-bg-1)] shrink-0">
		{#each navTabs as tab (tab.id)}
			<a
				href={tab.href}
				class="relative px-4 py-2 text-xs font-medium transition-colors
					{$page.url.pathname.startsWith(tab.href)
						? 'text-[var(--color-text-primary)]'
						: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}">
				{tab.label}
				{#if $page.url.pathname.startsWith(tab.href)}
					<span class="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-accent)] rounded-full" />
				{/if}
			</a>
		{/each}
	</nav>

	<!-- Main Content Area -->
	<main class="flex flex-1 overflow-hidden">
		<!-- Left Panel: Targets Sidebar -->
		<aside class="flex flex-col border-r border-[var(--color-border)] bg-[var(--color-bg-1)]" style="width: 260px; min-width: 200px; max-width: 400px;">
			<div class="flex items-center justify-between px-3 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-2)]">
				<span class="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Targets</span>
				<a
					href="/targets"
					class="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-3)] transition-colors"
					aria-label="Manage targets"
					title="Manage targets">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
					</svg>
				</a>
			</div>
			<div class="flex-1 overflow-auto p-2 space-y-1">
				<!-- Target items (static for now) -->
				<a href="/targets" class="block p-2 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] hover:border-[var(--color-border-light)] hover:bg-[var(--color-bg-3)] cursor-pointer transition-colors">
					<div class="flex items-center justify-between mb-1">
						<span class="text-sm font-medium text-[var(--color-text-primary)]">example.com</span>
						<span class="w-2 h-2 rounded-full bg-[var(--color-success)]" />
					</div>
					<div class="text-xs text-[var(--color-text-muted)] font-mono">192.168.1.1</div>
				</a>
				<a href="/targets" class="block p-2 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] hover:border-[var(--color-border-light)] hover:bg-[var(--color-bg-3)] cursor-pointer transition-colors">
					<div class="flex items-center justify-between mb-1">
						<span class="text-sm font-medium text-[var(--color-text-primary)]">api.service.dev</span>
						<span class="w-2 h-2 rounded-full bg-[var(--color-warning)]" />
					</div>
					<div class="text-xs text-[var(--color-text-muted)] font-mono">10.0.0.50</div>
				</a>
				<a href="/targets" class="block p-2 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] hover:border-[var(--color-border-light)] hover:bg-[var(--color-bg-3)] cursor-pointer transition-colors">
					<div class="flex items-center justify-between mb-1">
						<span class="text-sm font-medium text-[var(--color-text-primary)]">staging.internal</span>
						<span class="w-2 h-2 rounded-full bg-[var(--color-text-muted)]" />
					</div>
					<div class="text-xs text-[var(--color-text-muted)] font-mono">172.16.0.100</div>
				</a>
			</div>
		</aside>

		<!-- Center Panel: Main Content -->
		<div class="flex flex-col flex-1 overflow-hidden">
			<slot />
		</div>

		<!-- Right Panel: Details -->
		<aside class="flex flex-col border-l border-[var(--color-border)] bg-[var(--color-bg-1)]" style="width: 380px; min-width: 250px; max-width: 600px;">
			<div class="flex items-center justify-between px-3 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-2)]">
				<span class="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Details</span>
			</div>
			<div class="flex-1 overflow-auto p-4">
				<div class="flex flex-col items-center justify-center h-full text-center py-16">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-[var(--color-text-muted)] mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<p class="text-sm text-[var(--color-text-secondary)]">Select a target or task to view details</p>
				</div>
			</div>
		</aside>
	</main>

	<!-- Status Bar -->
	<footer class="flex items-center justify-between px-3 py-1 border-t border-[var(--color-border)] bg-[var(--color-bg-1)] text-xs text-[var(--color-text-muted)] shrink-0">
		<div class="flex items-center gap-3">
			<span>OSINTote v0.1.0</span>
		</div>
		<div class="flex items-center gap-3">
			<span id="clock" />
		</div>
	</footer>
</div>
