<script lang="ts">
	let {
		title,
		width = 'w-64',
		className = '',
		closable = false,
		collapsed = false
	} = $props();

	let panelClasses = $derived([
		'flex flex-col bg-[var(--color-bg-1)] border-r border-[var(--color-border-0)]',
		width,
		className
	].filter(Boolean).join(' '));

	function handleCollapse() {
		collapsed = !collapsed;
	}
</script>

<div class="{panelClasses}" role="complementary" aria-label={title}>
	<!-- Panel Header -->
	<div class="flex items-center justify-between px-3 py-2 border-b border-[var(--color-border-0)] bg-[var(--color-bg-2)]">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-2)] select-none">
			{title}
		</h3>
		<div class="flex items-center gap-1">
			{#if closable}
				<button
					class="p-1 rounded text-[var(--color-text-2)] hover:text-[var(--color-text-0)] hover:bg-[var(--color-bg-3)] transition-colors"
					onclick={handleCollapse}
					aria-label="Close panel"
					title="Close">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
					</svg>
				</button>
			{/if}
			<button
				class="p-1 rounded text-[var(--color-text-2)] hover:text-[var(--color-text-0)] hover:bg-[var(--color-bg-3)] transition-colors"
				onclick={handleCollapse}
				aria-label={collapsed ? 'Expand panel' : 'Collapse panel'}
				title={collapsed ? 'Expand' : 'Collapse'}>
				{#if collapsed}
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 6a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 6a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
					</svg>
				{:else}
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path d="M5 4a1 1 0 00-2 0v7.268a2 2 0 000 3.464V16a1 1 0 102 0v-1.268a2 2 0 000-3.464V4zM11 4a1 1 0 10-2 0v1.268a2 2 0 000 3.464V16a1 1 0 102 0V8.732a2 2 0 000-3.464V4z" />
					</svg>
				{/if}
			</button>
		</div>
	</div>

	<!-- Panel Body -->
	<div class="flex-1 overflow-auto" class:hidden={collapsed}>
		<slot />
	</div>
</div>
