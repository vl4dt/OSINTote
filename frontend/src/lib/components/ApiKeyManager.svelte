<!-- SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com> -->
<!-- SPDX-License-Identifier: MIT -->
<!-- API Key Manager — CRUD for external service credentials -->

<script lang="ts">
	import { apiService } from '$lib/api/real';
	import type { ApiKey } from '$lib/types';

	let keys: ApiKey[] = $state([]);
	let loading = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let showForm = $state(false);
	let editingKey = $state<ApiKey | null>(null);
	let keyName = $state('');
	let keySource = $state('');
	let keySecret = $state('');

	async function loadKeys(): Promise<void> {
		loading = true;
		error = null;
		try {
			keys = await apiService.getApiKeys();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load API keys';
		} finally {
			loading = false;
		}
	}

	function startAdd(): void {
		editingKey = null;
		keyName = '';
		keySource = '';
		keySecret = '';
		showForm = true;
	}

	function startEdit(key: ApiKey): void {
		editingKey = { ...key };
		keyName = key.name;
		keySource = key.source;
		keySecret = '';
		showForm = true;
	}

	async function saveKey(): Promise<void> {
		if (!keyName.trim() || !keySource.trim()) return;
		saving = true;
		error = null;
		try {
			if (editingKey) {
				const updates: Partial<ApiKey> = {
					name: keyName,
					source: keySource,
					key: keySecret || '****',
					primary: editingKey.primary,
					fallback: editingKey.fallback,
				};
				await apiService.updateApiKey(editingKey.id, updates);
			} else {
				await apiService.createApiKey({
					name: keyName,
					source: keySource,
					key: keySecret,
					primary: false,
					fallback: false,
				});
			}
			showForm = false;
			await loadKeys();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save API key';
		} finally {
			saving = false;
		}
	}

	async function deleteKey(id: string): Promise<void> {
		if (!confirm('Delete this API key?')) return;
		try {
			await apiService.deleteApiKey(id);
			await loadKeys();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to delete API key';
		}
	}

	async function setPrimary(id: string): Promise<void> {
		try {
			// Set all others to non-primary
			for (const k of keys) {
				if (k.id !== id) {
					await apiService.updateApiKey(k.id, { primary: false });
				}
			}
			await loadKeys();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to set primary';
		}
	}

	async function rotateKey(key: ApiKey): Promise<void> {
		const newKey = prompt(`Enter new key for ${key.name}:`);
		if (!newKey) return;
		try {
			await apiService.rotateApiKey(key.id, newKey);
			await loadKeys();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to rotate key';
		}
	}

	function maskKey(key: string): string {
		if (!key || key.length < 8) return '••••••••';
		return key.slice(0, 4) + '••••••••' + key.slice(-4);
	}

	$effect(() => {
		loadKeys();
	});
</script>

<div class="api-key-manager">
	<div class="manager-header">
		<h3 class="section-title">API Keys</h3>
		<button class="btn btn-primary" onclick={startAdd} disabled={loading}>
			+ Add Key
		</button>
	</div>

	{#if error}
		<div class="error-banner">
			{error}
			<button class="close-btn" onclick={() => error = null}>×</button>
		</div>
	{/if}

	<!-- Key Form -->
	{#if showForm}
		<div class="key-form">
			<label class="form-label">
				Key Name
				<input
					type="text"
					bind:value={keyName}
					placeholder="e.g., Shodan Primary"
					class="form-input" />
			</label>

			<label class="form-label">
				Source
				<input
					type="text"
					bind:value={keySource}
					placeholder="e.g., shodan, virustotal, openai"
					class="form-input" />
			</label>

			<label class="form-label">
				API Key
				<input
					type="password"
					bind:value={keySecret}
					placeholder={editingKey ? 'Leave blank to keep current' : 'sk-...'}
					class="form-input" />
			</label>

			<div class="key-form-actions">
				<button class="btn btn-primary" onclick={saveKey} disabled={saving}>
					{saving ? 'Saving...' : editingKey ? 'Update' : 'Create'}
				</button>
				<button class="btn btn-secondary" onclick={() => { showForm = false; editingKey = null; }}>
					Cancel
				</button>
			</div>
		</div>
	{/if}

	<!-- Key List -->
	{#if loading}
		<div class="loading-state">Loading API keys...</div>
	{:else if keys.length === 0}
		<div class="empty-state">No API keys configured. Add your first key to get started.</div>
	{:else}
		<div class="key-list">
			{#each keys as key (key.id)}
				<div class="key-item">
					<div class="key-info">
						<span class="key-name">{key.name}</span>
						<span class="key-source">{key.source}</span>
						<span class="key-masked">{maskKey(key.key)}</span>
					</div>
					<div class="key-meta">
						<span class="key-status {key.status}">
							{key.status === 'active' ? '●' : key.status === 'rate-limited' ? '◐' : key.status === 'failed' ? '✗' : '○'}
							{key.status}
						</span>
						{#if key.primary}
							<span class="key-badge primary">PRIMARY</span>
						{:else}
							<button class="btn-xs" onclick={() => setPrimary(key.id)}>Set Primary</button>
						{/if}
						<button class="btn-xs" onclick={() => rotateKey(key)}>Rotate</button>
						<button class="btn-xs" onclick={() => startEdit(key)}>Edit</button>
						<button class="btn-xs btn-danger" onclick={() => deleteKey(key.id)}>Del</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.api-key-manager {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.manager-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text-primary);
		margin: 0;
	}

	.btn {
		padding: 0.375rem 0.75rem;
		border-radius: 4px;
		font-size: 0.8125rem;
		cursor: pointer;
		border: 1px solid var(--color-border);
		background: var(--color-bg-subtle);
		color: var(--color-text);
		transition: background 0.2s;
	}

	.btn:hover:not(:disabled) {
		background: var(--color-bg-3);
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-primary {
		background: var(--color-accent);
		color: var(--color-text-on-emphasis);
		border: none;
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--color-accent-hover);
	}

	.btn-secondary {
		background: var(--color-bg-subtle);
		color: var(--color-text);
	}

	.btn-danger {
		color: var(--color-danger);
	}

	.error-banner {
		padding: 0.5rem 0.75rem;
		background: rgba(248, 81, 73, 0.15);
		border: 1px solid var(--color-danger);
		border-radius: 4px;
		color: var(--color-danger);
		font-size: 0.8125rem;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--color-danger);
		cursor: pointer;
		font-size: 1rem;
		padding: 0;
	}

	.key-form {
		padding: 0.75rem;
		background: var(--color-bg-subtle);
		border: 1px solid var(--color-border);
		border-radius: 6px;
	}

	.form-label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		margin-bottom: 0.75rem;
	}

	.form-input {
		padding: 0.5rem 0.75rem;
		background: var(--color-canvas-subtle);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		color: var(--color-text);
		font-size: 0.8125rem;
	}

	.form-input:focus {
		outline: none;
		border-color: var(--color-accent);
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

	.loading-state {
		text-align: center;
		padding: 1rem;
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}
</style>
