<script lang="ts">
	import { onMount } from 'svelte';

	onMount(() => {
		window.location.replace('/dashboard');
	});
</script>

<div class="flex items-center justify-center h-screen bg-[var(--color-bg-0)]">
	<div class="text-center">
		<div class="mb-4">
			<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-[var(--color-text-3)] mx-auto animate-spin" viewBox="0 0 24 24" fill="none">
				<path d="M12 2v4m0 12v4m-9.17-15.17l2.83 2.83m11.34 11.34l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m11.34-11.34l2.83-2.83" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
			</svg>
		</div>
		<p class="text-sm text-[var(--color-text-3)]">Loading OSINTote...</p>
	</div>
</div>
