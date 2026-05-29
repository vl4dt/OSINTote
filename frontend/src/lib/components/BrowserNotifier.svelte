<!-- SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com> -->
<!-- SPDX-License-Identifier: MIT -->
<!-- Browser Notification API wrapper for OSINTote Web UI -->

<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';

	export let enabled: boolean = false;

	let permission: NotificationPermission = 'default';

	function requestPermission(): Promise<boolean> {
		if (!browser) return Promise.resolve(false);
		if (!('Notification' in window)) return Promise.resolve(false);

		return Notification.requestPermission().then((perm) => {
			permission = perm;
			return perm === 'granted';
		});
	}

	function send(title: string, body: string, options?: NotificationOptions): void {
		if (!browser || !enabled || permission !== 'granted') return;

		if (!('Notification' in window)) return;

		try {
			new Notification(title, {
				body,
				icon: '/icon.png',
				...options,
			});
		} catch {
			// Notification failed — user may have blocked notifications
		}
	}

	onMount(async () => {
		if (browser && 'Notification' in window) {
			permission = window.Notification.permission;
			if (permission === 'default' && enabled) {
				await requestPermission();
			}
		}
	});

	export { requestPermission, send };
</script>
