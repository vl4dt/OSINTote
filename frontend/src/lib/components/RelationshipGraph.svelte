<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { Result, Target } from '$lib/types';

	let {
		results,
		targets,
		width = 800,
		height = 600,
	}: {
		results: Result[];
		targets: Target[];
		width?: number;
		height?: number;
	} = $props();

	let container: HTMLDivElement;
	let network: any = null;
	let loading = $state(true);
	let selectedNode: string | null = null;

	interface GraphData {
		nodes: Array<{
			id: string;
			label: string;
			group: string;
			size: number;
			color: {
				background: string;
				border: string;
				highlight: {
					background: string;
					border: string;
				};
			};
			title: string;
		}>;
		edges: Array<{
			from: string;
			to: string;
			label: string;
			color: {
				color: string;
			};
		}>;
	}

	const typeColors: Record<string, { bg: string; border: string }> = {
		target: { bg: '#58a6ff', border: '#1f6feb' },
		'dns-a': { bg: '#3fb950', border: '#238636' },
		'dns-aaaa': { bg: '#3fb950', border: '#238636' },
		'dns-mx': { bg: '#58a6ff', border: '#1f6feb' },
		'dns-ns': { bg: '#58a6ff', border: '#1f6feb' },
		'dns-txt': { bg: '#d29922', border: '#b0801e' },
		'dns-cname': { bg: '#58a6ff', border: '#1f6feb' },
		'http-response': { bg: '#3fb950', border: '#238636' },
		'whois': { bg: '#d29922', border: '#b0801e' },
		'virustotal': { bg: '#f85149', border: '#da3633' },
		'shodan': { bg: '#d29922', border: '#b0801e' },
		default: { bg: '#8b949e', border: '#6e7681' },
	};

	function getNodeColor(type: string): { bg: string; border: string } {
		return typeColors[type] || typeColors['default'];
	}

	function buildGraphData(): GraphData {
		const nodes: GraphData['nodes'] = [];
		const edges: GraphData['edges'] = [];
		const nodeMap = new Map<string, number>();
		let nextId = 0;

		// Add target nodes
		for (const target of targets) {
			const id = `target-${target.id}`;
			nodeMap.set(id, nextId);
			nodes.push({
				id: nextId,
				label: target.name || target.target,
				group: 'target',
				size: 25,
				color: {
					background: '#58a6ff',
					border: '#1f6feb',
					highlight: {
						background: '#79c0ff',
						border: '#58a6ff',
					},
				},
				title: `Target: ${target.name || target.target}`,
			});
			nextId++;
		}

		// Add target nodes from results if not in targets list
		for (const result of results) {
			const targetId = `target-${result.target}`;
			if (!nodeMap.has(targetId)) {
				const color = getNodeColor(result.type);
				nodeMap.set(targetId, nextId);
				nodes.push({
					id: nextId,
					label: result.target,
					group: 'target',
					size: 20,
					color: {
						background: color.bg,
						border: color.border,
						highlight: {
							background: color.bg,
							border: color.border,
						},
					},
					title: `Target: ${result.target}`,
				});
				nextId++;
			}
		}

		// Add finding nodes and edges
		for (const result of results) {
			const targetId = nodeMap.get(`target-${result.target}`);
			if (targetId === undefined) continue;

			const findingId = nextId;
			const color = getNodeColor(result.type);

			nodes.push({
				id: findingId,
				label: result.type,
				group: result.type,
				size: 12,
				color: {
					background: color.bg,
					border: color.border,
					highlight: {
						background: color.bg,
						border: color.border,
					},
				},
				title: `${result.type} — ${result.message || ''}`,
			});

			edges.push({
				from: String(targetId),
				to: String(findingId),
				label: result.type,
				color: {
					color: color.border,
				},
			});

			nextId++;
		}

		return { nodes, edges };
	}

	function initNetwork(): void {
		if (!container) return;

		const graphData = buildGraphData();

		// Load vis.js from CDN
		const script = document.createElement('script');
		script.src = 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js';
		script.onload = () => {
			loading = false;

			const data = {
				nodes: new (window as any).vis.DataSet(graphData.nodes),
				edges: new (window as any).vis.DataSet(graphData.edges),
			};

			const options = {
				physics: {
					enabled: true,
					stabilization: {
						iterations: 100,
						fit: true,
					},
					barnHut: {
						springLength: 100,
						springConstant: 0.001,
						damping: 0.09,
						avoidOverlap: 0.2,
					},
				},
				interaction: {
					hover: true,
					tooltipDelay: 100,
					zoomView: true,
					panView: true,
				},
				nodes: {
					font: {
						face: "'Fira Mono', monospace",
						size: 10,
						color: '#c9d1d9',
					},
					shadow: {
						enabled: true,
						x: 0,
						y: 0,
						blur: 2,
						color: 'rgba(88,166,255,0.3)',
					},
				},
				edges: {
					font: {
						face: "'Fira Mono', monospace",
						size: 8,
						color: '#484f58',
					},
					smooth: {
						type: 'curvedCW',
					roundness: 0.1,
					},
					arrows: 'to',
				},
				layout: {
					hierarchical: {
						enabled: false,
					},
				},
			};

			try {
				network = new (window as any).vis.Network(container, data, options);

				network.on('click', (event: any) => {
					const nodeId = event.nodes[0];
					if (nodeId) {
						selectedNode = String(nodeId);
					} else {
						selectedNode = null;
					}
				});

				network.on('hoverNode', (event: any) => {
					container.style.cursor = 'pointer';
				});

				network.on('blurNode', () => {
					container.style.cursor = 'default';
				});
			} catch (err) {
				console.error('Failed to initialize vis.Network:', err);
				loading = true;
			}
		};

		document.head.appendChild(script);
	}

	function fitView(): void {
		if (network) {
			network.fit({
				animation: {
					duration: 300,
					easingFunction: 'easeInOutQuad',
				},
			});
		}
	}

	onMount(() => {
		initNetwork();
	});

	onDestroy(() => {
		if (network) {
			network.destroy();
			network = null;
		}
	});

	function handleFitView(): void {
		setTimeout(fitView, 500);
	}

	const stats = $derived({
		targetCount: targets.length + new Set(results.map(r => r.target)).size,
		findingCount: results.length,
		typeCount: [...new Set(results.map(r => r.type))].length,
		edgeCount: results.length,
	});
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<span class="text-lg">🕸️</span>
				<h2 class="text-sm font-semibold text-[var(--color-text-primary)]">Relationship Graph</h2>
			</div>
			<div class="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
				<span>{stats.targetCount} targets</span>
				<span>·</span>
				<span>{stats.findingCount} findings</span>
				<span>·</span>
				<button
					class="px-2 py-0.5 rounded hover:bg-[var(--color-bg-3)] hover:text-[var(--color-text-primary)] transition-colors"
					onclick={handleFitView}>
					🔍 Fit
				</button>
			</div>
		</div>
	</div>

	<!-- Graph -->
	<div class="flex-1 relative overflow-hidden">
		{#if loading}
			<div class="absolute inset-0 flex items-center justify-center">
				<div class="flex flex-col items-center gap-3">
					<div class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
					<span class="text-xs text-[var(--color-text-muted)]">Loading graph...</span>
				</div>
			</div>
		{/if}
		<div bind:this={container} class="w-full h-full"></div>
	</div>

	<!-- Legend -->
	<div class="px-3 py-2 border-t border-[var(--color-border)] bg-[var(--color-bg-1)]">
		<div class="flex flex-wrap gap-2 text-xs">
			<span class="flex items-center gap-1">
				<span class="w-2.5 h-2.5 rounded-full bg-[#58a6ff]"></span>
				<span class="text-[var(--color-text-muted)]">Target</span>
			</span>
			{#each [...new Set(results.map(r => r.type))].sort() as type}
				{#if type}
					<span class="flex items-center gap-1">
						<span class="w-2.5 h-2.5 rounded-full" style="background: {getNodeColor(type).bg}"></span>
						<span class="text-[var(--color-text-muted)]">{type}</span>
					</span>
				{/if}
			{/each}
		</div>
	</div>

	<!-- Empty State -->
	{#if results.length === 0 && targets.length === 0}
		<div class="flex-1 flex items-center justify-center">
			<div class="flex flex-col items-center gap-2 text-center">
				<span class="text-3xl">📊</span>
				<p class="text-sm text-[var(--color-text-muted)]">No data to visualize</p>
				<p class="text-xs text-[var(--color-text-muted)]">Add targets and run tasks to see the relationship graph.</p>
			</div>
		</div>
	{/if}

	{#if results.length > 0 && targets.length === 0}
		<div class="flex-1 flex items-center justify-center">
			<div class="flex flex-col items-center gap-2 text-center">
				<span class="text-3xl">🔗</span>
				<p class="text-sm text-[var(--color-text-muted)]">Only findings visible — add targets for full relationships</p>
			</div>
		</div>
	{/if}
</div>

<style>
	#graph-container {
		width: 100%;
		height: 100%;
	}

	#graph-container canvas {
		display: block;
	}

	.vis-network {
		background: transparent;
	}
</style>
