<!-- SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com> -->
<!-- SPDX-License-Identifier: MIT -->
<!-- Settings Form — AI config, recipe, output format, theme -->

<script lang="ts">
	import { onMount } from 'svelte';
	import { apiService } from '$lib/api/mock';

	let activeTab: string = $state('ai');
	const { activeTab: _activeTab } = $props();
	$effect(() => { if (_activeTab !== undefined) activeTab = _activeTab; });

	interface AIConfig {
		provider: string;
		models: Record<string, string>;
		apiKey: string;
		baseUrl: string;
	}

	interface Settings {
		ai: AIConfig;
		defaultRecipe: string;
		outputFormat: string;
		theme: string;
	}

	const AI_PROVIDERS = ['openai', 'ollama', 'lmstudio', 'vllm', 'anthropic'];
	const OUTPUT_FORMATS = ['json', 'markdown', 'html'];

	let settings: Settings = $state({
		ai: {
			provider: 'openai',
			models: {
				analysis: '',
				query: '',
				suggest: ''
			},
			apiKey: '',
			baseUrl: ''
		},
		defaultRecipe: '',
		outputFormat: 'json',
		theme: 'dark'
	});

	let loaded = $state(false);
	let saving = $state(false);

	async function loadSettings(): Promise<void> {
		try {
			// Load from localStorage first
			const stored = localStorage.getItem('osintote-settings');
			if (stored) {
				settings = { ...settings, ...JSON.parse(stored) };
			}
			// Then try server sync
			const res = await fetch('/api/v1/settings', {
				credentials: 'include'
			});
			if (res.ok) {
				const data = await res.json();
				settings = { ...settings, ...data };
			}
		} catch {
			// Use defaults + localStorage
		}
		loaded = true;
	}

	async function saveSettings(): Promise<void> {
		saving = true;
		try {
			// Save to localStorage
			localStorage.setItem('osintote-settings', JSON.stringify(settings));
			// Sync to server
			await fetch('/api/v1/settings', {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(settings),
				credentials: 'include'
			});
		} catch (err) {
			console.error('Failed to save settings:', err);
		} finally {
			saving = false;
		}
	}

	// Auto-save on changes (debounced)
	let saveTimeout: ReturnType<typeof setTimeout>;
	$effect(() => {
		if (loaded) {
			clearTimeout(saveTimeout);
			saveTimeout = setTimeout(saveSettings, 500);
		}
	});

	onMount(() => {
		loadSettings();
	});

	const tabs = [
		{ id: 'ai', label: 'AI' },
		{ id: 'recipe', label: 'Recipes' },
		{ id: 'output', label: 'Output' },
		{ id: 'theme', label: 'Theme' }
	];
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
						placeholder={`http://localhost:8080/v1`}
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

			<div class="format-help">
				<p class="text-sm text-[var(--color-text-muted)]">
					{#if settings.outputFormat === 'json'}
						Structured JSON output — best for programmatic processing
					{:else if settings.outputFormat === 'markdown'}
						Markdown reports — human-readable with tables and summaries
					{:else}
						HTML reports — standalone with embedded styles and interactivity
					{/if}
				</p>
			</div>
		</div>
	{/if}

	<!-- Theme Tab -->
	{#if activeTab === 'theme'}
		<div class="settings-section">
			<h3 class="section-title">Appearance</h3>
			<label class="form-label">
				Theme
				<select bind:value={settings.theme} class="form-select">
					<option value="dark">Dark</option>
					<option value="light">Light</option>
					<option value="auto">Auto (System)</option>
				</select>
			</label>

			{#if settings.theme === 'auto'}
				<p class="text-xs text-[var(--color-text-muted)] mt-1">
					Detects system preference via prefers-color-scheme.
				</p>
			{/if}

			<div class="theme-preview">
				<button
					class="preview-btn"
					onclick={() => {
						document.documentElement.classList.toggle('light-theme');
					}}>
					Preview Theme
				</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.settings-form {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.settings-tabs {
		display: flex;
		gap: 0;
		border-bottom: 1px solid var(--color-border);
		padding: 0 1rem;
		background: var(--color-bg-subtle);
	}

	.settings-tab {
		padding: 0.75rem 1.25rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text-secondary);
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		cursor: pointer;
		transition: all 0.2s;
	}

	.settings-tab:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-inset);
	}

	.settings-tab.active {
		color: var(--color-text-primary);
		border-bottom-color: var(--color-accent);
	}

	.save-indicator {
		display: flex;
		justify-content: flex-end;
		padding: 0.25rem 1rem;
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	.saved-text {
		color: var(--color-success);
	}

	.settings-section {
		padding: 1rem;
		flex: 1;
		overflow-y: auto;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: 0.75rem;
	}

	.mt-4 {
		margin-top: 1rem;
	}

	.form-label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		margin-bottom: 1rem;
	}

	.form-input,
	.form-select {
		padding: 0.5rem 0.75rem;
		background: var(--color-canvas-subtle);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		color: var(--color-text);
		font-size: 0.875rem;
	}

	.form-input:focus,
	.form-select:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.form-input::placeholder {
		color: var(--color-text-muted);
	}

	.recipe-help,
	.format-help {
		margin-top: 0.5rem;
	}

	.theme-preview {
		margin-top: 1rem;
	}

	.preview-btn {
		padding: 0.5rem 1rem;
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		color: var(--color-text);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.preview-btn:hover {
		background: var(--color-bg-3);
	}
</style>
