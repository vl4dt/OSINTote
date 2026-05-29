<script lang="ts">
	import { onMount } from 'svelte';

	let {
		onClose,
		onSubmit,
		open = false,
		targetId = '',
		targetName = '',
		targetType = 'domain',
		targetTags = []
	} = $props<{
		onClose: () => void;
		onSubmit: (data: { name: string; type: string; tags: string[] }) => void;
		open?: boolean;
		targetId?: string;
		targetName?: string;
		targetType?: string;
		targetTags?: string[];
	}>();

	let name = $state(targetName);
	let type = $state(targetType);
	let tagsInput = $state('');
	let tags = $state<string[]>([...targetTags]);

	let error = $state('');
	let submitting = $state(false);

	// Add tag
	function addTag(): void {
		const tag = tagsInput.trim().toLowerCase();
		if (tag && !tags.includes(tag)) {
			tags = [...tags, tag];
			tagsInput = '';
		}
	}

	// Remove tag
	function removeTag(tag: string): void {
		tags = tags.filter(t => t !== tag);
	}

	function handleKeyDown(e: KeyboardEvent): void {
		if (e.key === 'Enter' && e.target === e.currentTarget) {
			e.preventDefault();
			addTag();
		}
	}

	async function handleSubmit(): Promise<void> {
		if (!name.trim()) {
			error = 'Target name is required';
			return;
		}
		if (tags.length > 20) {
			error = 'Maximum 20 tags allowed';
			return;
		}
		submitting = true;
		error = '';
		await onSubmit({ name: name.trim(), type, tags });
		submitting = false;
	}

	function handleClose(): void {
		onClose();
	}
</script>

{#if open}
	<!-- Overlay -->
	<div
		class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center"
		onclick={handleClose}>

		<!-- Dialog -->
		<div
			class="bg-[var(--color-bg-1)] border border-[var(--color-border)] rounded-lg shadow-xl w-full max-w-md mx-4"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => { if (e.key === 'Escape') handleClose(); }}>

			<!-- Header -->
			<div class="flex items-center justify-between px-5 py-3 border-b border-[var(--color-border)]">
				<h2 class="text-base font-semibold text-[var(--color-text-primary)]">
					{targetId ? 'Edit Target' : 'Add Target'}
				</h2>
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
					<label for="target-name" class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
						Name <span class="text-[var(--color-error)]">*</span>
					</label>
					<input
						id="target-name"
						type="text"
						value={name}
						placeholder="example.com, 192.168.1.0/24, admin.corp.local"
						class="w-full px-3 py-2 text-sm rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]/50 transition"
						oninput={(e) => { name = (e.target as HTMLInputElement).value; error = ''; }}
						onkeydown={(e) => { if (e.key === 'Enter') handleSubmit(); }} />
				</div>

				<!-- Type -->
				<div>
					<label for="target-type" class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
						Type
					</label>
					<select
						id="target-type"
						value={type}
						class="w-full px-3 py-2 text-sm rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)] transition">
						<option value="domain">Domain</option>
						<option value="hostname">Hostname</option>
						<option value="ip">IP Address</option>
						<option value="cidr">CIDR Range</option>
						<option value="email">Email Address</option>
						<option value="url">URL</option>
					</select>
				</div>

				<!-- Tags -->
				<div>
					<label for="tag-input" class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
						Tags
					</label>
					<div class="flex flex-wrap gap-1.5 mb-1.5">
						{#each tags as tag}
							<span class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-[var(--color-bg-3)] text-[var(--color-text-secondary)]">
								{tag}
								<button
									class="ml-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
									onclick={() => removeTag(tag)}
									aria-label={`Remove tag ${tag}`}>
									<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
										<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
									</svg>
								</button>
							</span>
						{/each}
					</div>
					<input
						id="tag-input"
						type="text"
						value={tagsInput}
						placeholder="Press Enter to add"
						class="w-full px-3 py-2 text-sm rounded-md border border-[var(--color-border)] bg-[var(--color-bg-2)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] transition"
						onkeydown={handleKeyDown}
						oninput={(e) => { tagsInput = (e.target as HTMLInputElement).value; }} />
					{#if tags.length >= 20}
						<p class="text-xs text-[var(--color-text-muted)] mt-1">Maximum 20 tags</p>
					{/if}
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
					{submitting ? 'Saving...' : targetId ? 'Update' : 'Add Target'}
				</button>
			</div>
		</div>
	</div>
{/if}
