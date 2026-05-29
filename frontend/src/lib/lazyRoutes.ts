/**
 * Lazy route loader for OSINTote.
 * Uses dynamic imports to split route code into separate chunks.
 */

type RouteModule = { default: any };

const routeImports: Record<string, () => Promise<RouteModule>> = {
	dashboard: () => import('../routes/dashboard/+page.svelte') as Promise<RouteModule>,
	targets: () => import('../routes/targets/+page.svelte') as Promise<RouteModule>,
	tasks: () => import('../routes/tasks/+page.svelte') as Promise<RouteModule>,
	results: () => import('../routes/results/+page.svelte') as Promise<RouteModule>,
	logs: () => import('../routes/logs/+page.svelte') as Promise<RouteModule>,
	settings: () => import('../routes/settings/+page.svelte') as Promise<RouteModule>,
};

/**
 * Lazy-load a route component by its path prefix.
 * Caches the import result after first load.
 * Returns undefined if not found.
 */
const cache: Record<string, any> = {};

export async function lazyRoute(route: string) {
	if (cache[route]) return cache[route];

	const importFn = routeImports[route];
	if (!importFn) return undefined;

	const module = await importFn();
	cache[route] = module.default;
	return cache[route];
}

/**
 * Pre-load all routes at startup (runs in background).
 * This avoids await in templates and enables true code splitting.
 */
export async function preloadAll() {
	await Promise.all(
		Object.values(routeImports).map((importFn) => importFn())
	);
}

/**
 * Type-safe route map for IDE autocomplete.
 */
export type RouteKey = keyof typeof routeImports;
