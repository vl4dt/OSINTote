<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	onMount(() => {
		if (browser) {
			window.location.href = '/dashboard';
		}
	});
</script>

<div class="flex flex-col items-center justify-center h-full gap-4">
	<div class="text-center">
		<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-[var(--color-accent)] mx-auto mb-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<circle cx="12" cy="12" r="10" />
			<line x1="2" y1="12" x2="22" y2="12" />
			<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
		</svg>
		<p class="text-sm text-[var(--color-text-muted)]">Loading OSINTote...</p>
	</div>
</div>
