<!-- SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com> -->
<!-- SPDX-License-Identifier: MIT -->
<!-- SSE Stream — EventSource-based real-time task progress -->

<script lang="ts">
	import { browser } from '$app/environment';
	import type { SSEEvent } from '$lib/types';

	let {
		url = '/api/events',
		onEvent,
		autoConnect = true
	}: {
		url?: string;
		onEvent: (event: SSEEvent) => void;
		autoConnect?: boolean;
	} = $props();

	let eventSource: EventSource | null = $state(null);
	let connected = $state(false);
	let lastEvent = $state<SSEEvent | null>(null);
	let error = $state<string | null>(null);

	let reconnectTimer: ReturnType<typeof setTimeout> | null = $state(null);

	function connect(): void {
		if (!browser || eventSource) return;

		eventSource = new EventSource(url);

		eventSource.onopen = () => {
			connected = true;
			error = null;
		};

		eventSource.onmessage = (e: MessageEvent) => {
			try {
				const data = JSON.parse(e.data);
				const event: SSEEvent = {
					...data,
					timestamp: data.timestamp || new Date().toISOString().replace('T', ' ').slice(0, 19)
				};
				onEvent(event);
				lastEvent = event;
			} catch {
				// Skip non-JSON messages (ping, etc.)
			}
		};

		eventSource.onerror = () => {
			connected = false;
			error = 'Connection lost. Reconnecting...';
			eventSource?.close();
			eventSource = null;

			reconnectTimer = setTimeout(connect, 3000);
		};
	}

	function disconnect(): void {
		if (reconnectTimer) {
			clearTimeout(reconnectTimer);
			reconnectTimer = null;
		}
		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}
		connected = false;
	}

	$effect(() => {
		if (autoConnect && browser) {
			connect();
			return () => disconnect();
		}
	});
</script>

<!-- Hidden SSE connector with optional status indicator -->
{#if !connected && browser}
	<div class="fixed bottom-2 right-2 z-50 px-2 py-1 text-[10px] rounded bg-[var(--color-bg-3)] text-[var(--color-text-muted)]">
		SSE: {error || 'connecting...'}
	</div>
{/if}

{#if connected}
	<div class="fixed bottom-2 right-2 z-50 px-2 py-1 text-[10px] rounded bg-[color:rgba(63,185,80,0.15)] text-[var(--color-success)]">
		SSE: connected
	</div>
{/if}
