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

	interface APIKey {
		id: string;
		name: string;
		source: string;
		key: string;
		status: 'active' | 'rate-limited' | 'failed';
		isPrimary: boolean;
		createdAt: string;
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

	// --- API Key Management ---

	function maskKey(key: string): string {
		if (!key || key.length < 8) return '••••••••';
		return key.slice(0, 4) + '••••••••' + key.slice(-4);
	}

	function setStatus(keyId: string, status: 'active' | 'rate-limited' | 'failed'): void {
		const key = apiKeys.find(k => k.id === keyId);
		if (key) key.status = status;
	}

	function startAdd(): void {
		editingKey = null;
		keyName = '';
		keySource = '';
		keySecret = '';
		showKeyForm = true;
	}

	function startEdit(key: APIKey): void {
		editingKey = { ...key };
		keyName = key.name;
		keySource = key.source;
		keySecret = '';
		showKeyForm = true;
	}

	function saveKey(): void {
		if (editingKey) {
			const idx = apiKeys.findIndex(k => k.id === editingKey!.id);
			if (idx !== -1) {
				apiKeys[idx] = {
					...apiKeys[idx],
					name: keyName,
					source: keySource,
					key: keySecret || apiKeys[idx].key
				};
			}
		} else {
			apiKeys.push({
				id: `key-${Date.now()}`,
				name: keyName,
				source: keySource,
				key: keySecret || '••••••••',
				status: 'active',
				isPrimary: apiKeys.length === 0,
				createdAt: new Date().toISOString()
			});
		}
		showKeyForm = false;
		editingKey = null;
	}

	function deleteKey(id: string): void {
		apiKeys = apiKeys.filter(k => k.id !== id);
	}

	function setPrimary(id: string): void {
		apiKeys.forEach(k => {
			k.isPrimary = k.id === id;
		});
	}

	function cancelKey(): void {
		showKeyForm = false;
		editingKey = null;
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
		{ id: 'keys', label: 'API Keys' },
		{ id: 'recipe', label: 'Recipes' },
		{ id: 'output', label: 'Output' },
		{ id: 'theme', label: 'Theme' }
	];

	// --- API Keys State ---
	let apiKeys: APIKey[] = $state([]);
	let editingKey: APIKey | null = $state(null);
	let showKeyForm: boolean = $state(false);
	let keyName: string = $state('');
	let keySource: string = $state('');
	let keySecret: string = $state('');
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
		<div class="settings-section">
			<div class="keys-header">
				<h3 class="section-title">API Keys</h3>
				<button class="btn btn-sm btn-primary" onclick={startAdd}>
					+ Add Key
				</button>
			</div>

			<!-- Key Form (add/edit) -->
			{#if showKeyForm}
				<div class="key-form">
					<label class="form-label">
						Key Name
						<input
							type="text"
							bind:value={keyName}
							placeholder="e.g., OpenAI Primary"
							class="form-input" />
					</label>

					<label class="form-label">
						Source
						<input
							type="text"
							bind:value={keySource}
							placeholder="e.g., OpenAI, Anthropic, Custom"
							class="form-input" />
					</label>

					<label class="form-label">
						Secret Key
						<input
							type="password"
							bind:value={keySecret}
							placeholder={editingKey ? 'Leave blank to keep current' : 'sk-...'}
							class="form-input" />
					</label>

					<div class="key-form-actions">
						<button class="btn btn-sm btn-primary" onclick={saveKey}>
							{editingKey ? 'Update' : 'Create'}
						</button>
						<button class="btn btn-sm btn-secondary" onclick={cancelKey}>
							Cancel
						</button>
					</div>
				</div>
			{/if}

			<!-- Key List -->
			<div class="key-list">
				{#each apiKeys as key (key.id)}
					<div class="key-item">
						<div class="key-info">
							<span class="key-name">{key.name}</span>
							<span class="key-source">{key.source}</span>
							<span class="key-masked">{maskKey(key.key)}</span>
						</div>
						<div class="key-meta">
							<span class="key-status {key.status}">
								{key.status === 'active' ? '●' : key.status === 'rate-limited' ? '◐' : '○'}
								{key.status}
							</span>
							{#if key.isPrimary}
								<span class="key-badge primary">PRIMARY</span>
							{:else}
								<button class="btn btn-xs" onclick={() => setPrimary(key.id)}>Set Primary</button>
							{/if}
							<button class="btn btn-xs btn-danger" onclick={() => deleteKey(key.id)}>Del</button>
							<button class="btn btn-xs" onclick={() => startEdit(key)}>Edit</button>
						</div>
					</div>
				{:else}
					<div class="empty-state">No API keys configured.</div>
				{/each}
			</div>
		</div>
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

	/* --- API Keys --- */
	.keys-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.btn-primary {
		background: var(--color-accent);
		color: var(--color-text-on-emphasis);
	}

	.btn-danger {
		color: var(--color-danger);
	}

	.btn-xs {
		padding: 0.125rem 0.375rem;
		font-size: 0.6875rem;
		border: 1px solid var(--color-border);
		border-radius: 3px;
		background: var(--color-bg-subtle);
		color: var(--color-text);
		cursor: pointer;
	}

	.btn-xs:hover {
		background: var(--color-bg-3);
	}

	.key-form {
		padding: 0.75rem;
		margin-bottom: 1rem;
		background: var(--color-bg-subtle);
		border: 1px solid var(--color-border);
		border-radius: 6px;
	}

	.key-form-actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.5rem;
	}

	.key-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.key-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: var(--color-bg-subtle);
		border: 1px solid var(--color-border);
		border-radius: 6px;
	}

	.key-info {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.key-name {
		font-weight: 600;
		color: var(--color-text-primary);
		font-size: 0.875rem;
	}

	.key-source {
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	.key-masked {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.key-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.key-status {
		font-size: 0.75rem;
		padding: 0.125rem 0.5rem;
		border-radius: 9999px;
	}

	.key-status.active {
		background: rgba(63, 185, 80, 0.15);
		color: var(--color-success);
	}

	.key-status.rate-limited {
		background: rgba(210, 153, 34, 0.15);
		color: var(--color-warning);
	}

	.key-status.failed {
		background: rgba(248, 81, 73, 0.15);
		color: var(--color-danger);
	}

	.key-badge {
		font-size: 0.625rem;
		font-weight: 700;
		padding: 0.125rem 0.375rem;
		border-radius: 3px;
		background: var(--color-accent);
		color: var(--color-text-on-emphasis);
	}

	.key-badge.primary {
		background: var(--color-accent);
	}
</style>
