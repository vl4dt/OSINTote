<script lang="ts">
	let {
		leftPanel = true,
		centerPanel = true,
		rightPanel = true
	} = $props();

	let leftVisible = $state(leftPanel);
	let centerVisible = $state(centerPanel);
	let rightVisible = $state(rightPanel);

	let leftWidth = $state(280);
	let rightWidth = $state(480);

	let isResizingLeft = $state(false);
	let isResizingRight = $state(false);

	function handleMouseDownLeft(e: MouseEvent) {
		e.preventDefault();
		isResizingLeft = true;
		const startX = e.clientX;
		const startWidth = leftWidth;

		function onMouseMove(e: MouseEvent) {
			if (!isResizingLeft) return;
			const diff = e.clientX - startX;
			const newWidth = Math.max(200, Math.min(500, startWidth + diff));
			leftWidth = newWidth;
		}

		function onMouseUp() {
			isResizingLeft = false;
			document.removeEventListener('mousemove', onMouseMove);
			document.removeEventListener('mouseup', onMouseUp);
		}

		document.addEventListener('mousemove', onMouseMove);
		document.addEventListener('mouseup', onMouseUp);
	}

	function handleMouseDownRight(e: MouseEvent) {
		e.preventDefault();
		isResizingRight = true;
		const startX = e.clientX;
		const startWidth = rightWidth;

		function onMouseMove(e: MouseEvent) {
			if (!isResizingRight) return;
			const diff = e.clientX - startX;
			const newWidth = Math.max(250, Math.min(700, startWidth - diff));
			rightWidth = newWidth;
		}

		function onMouseUp() {
			isResizingRight = false;
			document.removeEventListener('mousemove', onMouseMove);
			document.removeEventListener('mouseup', onMouseUp);
		}

		document.addEventListener('mousemove', onMouseMove);
		document.addEventListener('mouseup', onMouseUp);
	}

	const toggleLeft = () => { leftVisible = !leftVisible; };
	const toggleCenter = () => { centerVisible = !centerVisible; };
	const toggleRight = () => { rightVisible = !rightVisible; };
</script>

<div class="flex h-screen w-full bg-[var(--color-bg-0)] overflow-hidden">
	<!-- Left Panel: Targets/Navigation -->
	{#if leftVisible}
		<div
			class="relative flex flex-col border-r border-[var(--color-border-0)]"
			style="width: {leftWidth}px; min-width: 200px; max-width: 500px;">
			<slot name="left" />
		</div>

		<!-- Resize Handle -->
		<div
			class="absolute top-0 h-full cursor-col-resize z-10 hover:bg-[var(--color-accent)]/20 transition-colors"
			style="left: {leftWidth}px; width: 3px;"
			on:mousedown={handleMouseDownLeft}
			aria-label="Resize left panel" />
	{/if}

	<!-- Center Panel: Tasks/Activity -->
	{#if centerVisible}
		<div class="flex flex-col min-w-[280px] flex-1">
			<slot name="center" />
		</div>
	{/if}

	<!-- Right Panel: Details/Output -->
	{#if rightVisible}
		<!-- Resize Handle -->
		{#if centerVisible}
			<div
				class="absolute top-0 h-full cursor-col-resize z-10 hover:bg-[var(--color-accent)]/20 transition-colors"
				on:mousedown={handleMouseDownRight}
				aria-label="Resize right panel" />
		{/if}

		<div
			class="relative flex flex-col border-l border-[var(--color-border-0)]"
			style="width: {rightWidth}px; min-width: 250px; max-width: 700px;">
			<slot name="right" />
		</div>
	{/if}
</div>

<!-- Panel toggle buttons (visible when panels are collapsed) -->
{#if !leftVisible}
	<button
		class="absolute left-0 top-2 z-20 p-1 rounded-r border border-l-0 border-[var(--color-border-0)] bg-[var(--color-bg-1)] text-[var(--color-text-2)] hover:text-[var(--color-text-0)] hover:bg-[var(--color-bg-3)]"
		on:click={toggleLeft}
		aria-label="Show left panel">
		<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
			<path fill-rule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
		</svg>
	</button>
{/if}

{#if !rightVisible}
	<button
		class="absolute right-0 top-2 z-20 p-1 rounded-l border border-r-0 border-[var(--color-border-0)] bg-[var(--color-bg-1)] text-[var(--color-text-2)] hover:text-[var(--color-text-0)] hover:bg-[var(--color-bg-3)]"
		on:click={toggleRight}
		aria-label="Show right panel">
		<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
			<path fill-rule="evenodd" d="M4 5a1 1 0 000 2h8a1 1 0 100-2H4zm0 6a1 1 0 100 2h8a1 1 0 100-2H4zm0 6a1 1 0 100 2h8a1 1 0 100-2H4z" clip-rule="evenodd" />
		</svg>
	</button>
{/if}
