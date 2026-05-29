<script lang="ts">
	export let title: string = 'No items';
	export let description: string = '';
	export let actionLabel: string = '';
	export let onAction: () => void = () => {};
</script>

<div class="flex flex-col items-center justify-center h-full py-16 px-4 text-center">
	<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-[var(--color-text-3)] mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
		<path stroke-linecap="round" stroke-linejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
	</svg>

	<h3 class="text-base font-medium text-[var(--color-text-1)] mb-1">
		{title}
	</h3>

	{#if description}
		<p class="text-sm text-[var(--color-text-2)] max-w-sm mb-4">
			{description}
		</p>
	{/if}

	{#if actionLabel}
		<button
			class="mt-2 px-3 py-1.5 text-sm font-medium rounded-md border border-[var(--color-border-1)] text-[var(--color-text-1)] hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-0)] transition-colors"
			on:click={onAction}>
			{actionLabel}
		</button>
	{/if}
</div>
