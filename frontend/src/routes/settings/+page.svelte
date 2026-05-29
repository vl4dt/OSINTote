<!-- SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com> -->
<!-- SPDX-License-Identifier: MIT -->
<!-- Settings Page — AI config, recipes, output format, theme -->

<script lang="ts">
	import SettingsForm from '$lib/components/SettingsForm.svelte';
</script>

<div class="page-container">
	<h1 class="page-title">Settings</h1>
	<p class="page-subtitle">Configure AI providers, recipes, output format, and appearance</p>
	<SettingsForm />
</div>

<style>
	.page-container {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.page-title {
		margin: 0 0 0.25rem;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.page-subtitle {
		margin: 0 0 1rem;
		font-size: 0.875rem;
		color: var(--color-text-muted);
	}
</style>
