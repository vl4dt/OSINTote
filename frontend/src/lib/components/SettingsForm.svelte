<!-- SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com> -->
<!-- SPDX-License-Identifier: MIT -->
<!-- Settings Form — AI config, recipes, output format, theme -->

<script lang="ts">
	import { apiService } from '$lib/api/real';
	import ApiKeyManager from '$lib/components/ApiKeyManager.svelte';

	let activeTab: string = $state('ai');
	const { activeTab: _activeTab } = $props();
	$effect(() => { if (_activeTab !== undefined) activeTab = _activeTab; });

	let loaded = $state(false);

	// --- Settings State ---
	let settings: Record<string, unknown> = $state({
		ai: {
			provider: 'openai',
			models: { analysis: '', query: '', suggest: '' },
			apiKey: '',
			baseUrl: '',
		},
		defaultRecipe: '',
		outputFormat: 'json',
		theme: 'dark',
	});

	const AI_PROVIDERS = ['openai', 'ollama', 'lmstudio', 'vllm', 'anthropic'];
	const OUTPUT_FORMATS = ['json', 'markdown', 'html'];

	const tabs = [
		{ id: 'ai', label: 'AI Provider' },
		{ id: 'recipe', label: 'Recipe' },
		{ id: 'output', label: 'Output' },
		{ id: 'theme', label: 'Theme' },
		{ id: 'keys', label: 'API Keys' },
	];

	async function loadSettings(): Promise<void> {
		try {
			const stored = localStorage.getItem('osintote-settings');
			if (stored) {
				settings = { ...settings, ...JSON.parse(stored) };
			}
			const res = await fetch('/api/v1/settings', { credentials: 'include' });
			if (res.ok) {
				const data = await res.json();
				settings = { ...settings, ...data };
			}
		} catch {
			// Use defaults + localStorage
		}
		loaded = true;
	}

	let saving = $state(false);
	let saveTimeout: ReturnType<typeof setTimeout>;

	async function saveSettings(): Promise<void> {
		saving = true;
		try {
			localStorage.setItem('osintote-settings', JSON.stringify(settings));
			await fetch('/api/v1/settings', {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(settings),
				credentials: 'include',
			});
		} catch (err) {
			console.error('Failed to save settings:', err);
		} finally {
			saving = false;
		}
	}

	function setTab(tab: string): void {
		activeTab = tab;
	}

	$effect(() => {
		if (loaded) {
			clearTimeout(saveTimeout);
			saveTimeout = setTimeout(saveSettings, 500);
		}
	});

	$effect(() => {
		loadSettings();
	});
</script>

<div class="settings-form">
	<!-- Tab Navigation -->
	<div class="settings-tabs">
		{#each tabs as tab (tab.id)}
			<button
				class="settings-tab"
				class:active={activeTab === tab.id}
				onclick={() => setTab(tab.id)}>
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Save Indicator -->
	<div class="save-indicator">
		{#if saving}
			<span class="saving-text">Saving...</span>
		{:else if loaded}
			<span class="saved-text">Saved</span>
		{/if}
	</div>

	<!-- API Keys Tab -->
	{#if activeTab === 'keys'}
		<ApiKeyManager />
	{/if}

	<!-- AI Configuration Tab -->
	{#if activeTab === 'ai'}
		<div class="settings-section">
			<h3 class="section-title">AI Provider</h3>
			<label class="form-label">
				Provider
				<select bind:value={settings.ai.provider} class="form-select">
					{#each AI_PROVIDERS as provider}
						<option value={provider}>{provider}</option>
					{/each}
				</select>
			</label>

			{#if settings.ai.provider}
				<label class="form-label">
					Base URL
					<input
						type="url"
						bind:value={settings.ai.baseUrl}
						placeholder="http://localhost:8080/v1"
						class="form-input" />
				</label>

				<label class="form-label">
					API Key
					<input
						type="password"
						bind:value={settings.ai.apiKey}
						placeholder="sk-..."
						class="form-input" />
				</label>
			{/if}

			<h3 class="section-title mt-4">Models by Role</h3>
			<label class="form-label">
				Analysis Model
				<input
					type="text"
					bind:value={settings.ai.models.analysis}
					placeholder="gpt-4o"
					class="form-input" />
			</label>

			<label class="form-label">
				Query Model
				<input
					type="text"
					bind:value={settings.ai.models.query}
					placeholder="gpt-4o-mini"
					class="form-input" />
			</label>

			<label class="form-label">
				Suggestion Model
				<input
					type="text"
					bind:value={settings.ai.models.suggest}
					placeholder="gpt-3.5-turbo"
					class="form-input" />
			</label>
		</div>
	{/if}

	<!-- Recipe Settings Tab -->
	{#if activeTab === 'recipe'}
		<div class="settings-section">
			<h3 class="section-title">Default Recipe</h3>
			<label class="form-label">
				Default Recon Recipe
				<select bind:value={settings.defaultRecipe} class="form-select">
					<option value="">None</option>
					<option value="basic">Basic</option>
					<option value="full">Full Investigation</option>
					<option value="quick">Quick Overview</option>
				</select>
			</label>

			<div class="recipe-help">
				<p class="text-sm text-[var(--color-text-muted)]">
					The default recipe is used when creating a new task without selecting one.
				</p>
			</div>
		</div>
	{/if}

	<!-- Output Format Tab -->
	{#if activeTab === 'output'}
		<div class="settings-section">
			<h3 class="section-title">Output Format</h3>
			<label class="form-label">
				Default Report Format
				<select bind:value={settings.outputFormat} class="form-select">
					{#each OUTPUT_FORMATS as format}
						<option value={format}>{format}</option>
					{/each}
				</select>
			</label>
		</div>
	{/if}

	<!-- Theme Tab -->
	{#if activeTab === 'theme'}
		<div class="settings-section">
			<h3 class="section-title">Theme</h3>
			<label class="form-label">
				Interface Theme
				<select bind:value={settings.theme} class="form-select">
					<option value="dark">Dark</option>
					<option value="light">Light</option>
					<option value="auto">System</option>
				</select>
			</label>

			<div class="theme-preview">
				<p class="text-sm text-[var(--color-text-muted)]">
					Theme changes apply immediately to the current session.
				</p>
			</div>
		</div>
	{/if}
</div>

<style>
	.settings-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding: 0.5rem;
	}

	.settings-tabs {
		display: flex;
		gap: 0.25rem;
		border-bottom: 1px solid var(--color-border);
		padding-bottom: 0;
	}

	.settings-tab {
		padding: 0.5rem 1rem;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--color-text-muted);
		font-size: 0.8125rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.settings-tab:hover {
		color: var(--color-text);
	}

	.settings-tab.active {
		color: var(--color-text-primary);
		border-bottom-color: var(--color-accent);
		font-weight: 600;
	}

	.save-indicator {
		text-align: right;
		font-size: 0.75rem;
	}

	.saving-text {
		color: var(--color-warning);
	}

	.saved-text {
		color: var(--color-success);
	}

	.settings-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		padding: 1rem;
		background: var(--color-bg-subtle);
		border: 1px solid var(--color-border);
		border-radius: 6px;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text-primary);
		margin: 0;
	}

	.mt-4 {
		margin-top: 1rem;
	}

	.form-label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.form-input,
	.form-select {
		padding: 0.5rem 0.75rem;
		background: var(--color-canvas-subtle);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		color: var(--color-text);
		font-size: 0.8125rem;
	}

	.form-input:focus,
	.form-select:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.recipe-help,
	.theme-preview {
		font-size: 0.8125rem;
	}
</style>
