<script lang="ts">
	let {
		onClose,
		onSubmit,
		open = false,
		targetId = ''
	} = $props<{
		onClose: () => void;
		onSubmit: (data: { name: string; type: string; targetId: string; recipeId?: string }) => void;
		open?: boolean;
		targetId?: string;
	}>();

	let name = $state('');
	let taskType = $state('dns-enumerate');
	let target = $state(targetId);
	let recipeId = $state('');

	let error = $state('');
	let submitting = $state(false);

	const taskTypes = [
		{ value: 'dns-enumerate', label: 'DNS Enumeration', emoji: '🌐' },
		{ value: 'nmap', label: 'Nmap Scan', emoji: '🔍' },
		{ value: 'http-probe', label: 'HTTP Probe', emoji: '🌍' },
		{ value: 'whois', label: 'WHOIS Lookup', emoji: '📋' },
		{ value: 'subdomain', label: 'Subdomain Brute Force', emoji: '🔎' },
		{ value: 'cert-scan', label: 'Certificate Scan', emoji: '🔒' },
		{ value: 'vuln-scan', label: 'Vulnerability Scan', emoji: '🛡️' },
		{ value: 'api-scan', label: 'API Scan', emoji: '🔌' },
		{ value: 'custom', label: 'Custom', emoji: '⚡' }
	];

	const recipes = [
		{ id: 'quick-scan', label: 'Quick Scan', desc: 'DNS + HTTP probe only' },
		{ id: 'full-scan', label: 'Full Scan', desc: 'DNS + Nmap + HTTP + WHOIS' },
		{ id: 'vuln-full', label: 'Vuln Full', desc: 'Full scan + vulnerability check' },
		{ id: 'stealth', label: 'Stealth', desc: 'Low-rate, minimal footprint' }
	];

	async function handleSubmit(): Promise<void> {
		if (!name.trim()) {
			error = 'Task name is required';
			return;
		}
		if (!target) {
			error = 'Target is required';
			return;
		}
		submitting = true;
		error = '';
		await onSubmit({ name: name.trim(), type: taskType, targetId: target, recipeId: recipeId || undefined });
		submitting = false;
		name = '';
		recipeId = '';
	}

	function handleClose(): void {
		onClose();
	}
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center"
		onclick={handleClose}>

		<div
			class="bg-[var(--color-bg-1)] border border-[var(--color-border)] rounded-lg shadow-xl w-full max-w-md mx-4"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => { if (e.key === 'Escape') handleClose(); }}>

			<!-- Header -->
			<div class="flex items-center justify-between px-5 py-3 border-b border-[var(--color-border)]">
				<h2 class="text-base font-semibold text-[var(--color-text-primary)]">Create New Task</h2>
				<button
					class="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-3)]"
					onclick={handleClose}
					aria-label="Close">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
					</svg>
				</button>
			</div>

			<!-- Body -->
			<div class="px-5 py-4 space-y-4">
				<!-- Name -->
				<div>
					<label for="task-name" class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
						Name <span class="text-[var(--color-error)]">*</span>
					</label>
					<input
						id="task-name"
						type="text"
						value={name}
						placeholder="e.g., Port scan: example.com"
						class="w-full px-3 py-2 text-sm rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] transition"
						oninput={(e) => { name = (e.target as HTMLInputElement).value; error = ''; }}
						onkeydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) handleSubmit(); }} />
				</div>

				<!-- Target -->
				<div>
					<label for="task-target" class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
						Target ID <span class="text-[var(--color-error)]">*</span>
					</label>
					<input
						id="task-target"
						type="text"
						value={target}
						placeholder="tgt-001, tgt-002, etc."
						class="w-full px-3 py-2 text-sm rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] transition font-mono"
						oninput={(e) => { target = (e.target as HTMLInputElement).value; error = ''; }} />
				</div>

				<!-- Task Type -->
				<div>
					<label class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
						Task Type
					</label>
					<div class="grid grid-cols-2 gap-1.5">
						{#each taskTypes as t}
							<button
								class="flex items-center gap-2 px-3 py-2 text-xs rounded-md border transition-all
									{taskType === t.value
										? 'border-[var(--color-accent)] bg-[color:rgba(88,166,255,0.08)] text-[var(--color-text-primary)]'
										: 'border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-primary)]'}"
								onclick={() => { taskType = t.value; }}>
								<span>{t.emoji}</span>
								<span class="truncate">{t.label}</span>
							</button>
						{/each}
					</div>
				</div>

				<!-- Recipe -->
				<div>
					<label for="task-recipe" class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
						Recipe (optional)
					</label>
					<select
						id="task-recipe"
						value={recipeId}
						class="w-full px-3 py-2 text-sm rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)] transition">
						<option value="">None</option>
						{#each recipes as r}
							<option value={r.id}>{r.label} — {r.desc}</option>
						{/each}
					</select>
				</div>

				{#if error}
					<p class="text-xs text-[var(--color-error)]">{error}</p>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-2 px-5 py-3 border-t border-[var(--color-border)]">
				<button
					class="px-3 py-1.5 text-sm font-medium rounded-md border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-primary)] transition"
					onclick={handleClose}>
					Cancel
				</button>
				<button
					class="px-3 py-1.5 text-sm font-medium rounded-md bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 disabled:cursor-not-allowed"
					onclick={handleSubmit}
					disabled={submitting}>
					{submitting ? 'Creating...' : 'Create Task'}
				</button>
			</div>
		</div>
	</div>
{/if}
