<script lang="ts">
	export let tabs: { id: string; label: string; icon?: string; badge?: number }[];
	export let activeTab: string;
</script>

<nav class="flex items-center border-b border-[var(--color-border-0)] bg-[var(--color-bg-1)]" role="tablist" aria-label="Main navigation">
	{#each tabs as tab (tab.id)}
		<button
			class="relative flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors
				{tab.id === activeTab
					? 'text-[var(--color-text-0)] border-b-2 border-[var(--color-accent)]'
					: 'text-[var(--color-text-2)] hover:text-[var(--color-text-1)] hover:bg-[var(--color-bg-2)]'}"
			role="tab"
			aria-selected={tab.id === activeTab}
			aria-controls={`panel-${tab.id}`}
			on:click>
			<span>{tab.label}</span>
			{#if tab.badge}
				<span class="ml-1 px-1.5 py-0.5 text-xs font-medium rounded-full bg-[var(--color-bg-3)] text-[var(--color-text-2)]">
					{tab.badge}
				</span>
			{/if}
		</button>
	{/each}
</nav>
