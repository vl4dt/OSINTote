/**
 * Real API service — talks to the FastAPI backend at :8000.
 * Converts backend snake_case → frontend camelCase.
 */

import type { ApiKey, SSEEvent, Target, Task, Result } from '$lib/types';

const BASE = 'http://127.0.0.1:8000/api';

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		headers: { 'Content-Type': 'application/json', ...((init?.headers as Record<string, string>) || {}) },
		...init,
	});
	if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
	if (res.status === 204) return undefined as unknown as T;
	return res.json();
}

function snakeToCamel(obj: Record<string, unknown>): Record<string, unknown> {
	if (obj === null || typeof obj !== 'object') return obj;
	const result: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(obj)) {
		const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
		result[camelKey] = snakeToCamel(value as Record<string, unknown>);
	}
	return result;
}

export interface APIService {
	getTargets(): Promise<Target[]>;
	getTarget(id: string): Promise<Target | null>;
	createTarget(target: Omit<Target, 'id' | 'createdAt' | 'updatedAt'>): Promise<Target>;
	updateTarget(id: string, updates: Partial<Target>): Promise<Target>;
	deleteTarget(id: string): Promise<void>;

	getTasks(): Promise<Task[]>;
	getTask(id: string): Promise<Task | null>;
	createTask(task: Omit<Task, 'id' | 'createdAt' | 'updatedAt' | 'progress' | 'recordsCount'>): Promise<Task>;
	updateTask(id: string, updates: Partial<Task>): Promise<Task>;
	deleteTask(id: string): Promise<void>;
	startTask(id: string): Promise<Task>;
	cancelTask(id: string): Promise<Task>;

	getResults(): Promise<Result[]>;
	getResultsByTask(taskId: string): Promise<Result[]>;
	getResult(id: string): Promise<Result | null>;

	getApiKeys(): Promise<ApiKey[]>;
	getApiKey(id: string): Promise<ApiKey | null>;
	createApiKey(apiKey: Omit<ApiKey, 'id' | 'createdAt' | 'updatedAt' | 'status'>): Promise<ApiKey>;
	updateApiKey(id: string, updates: Partial<ApiKey>): Promise<ApiKey>;
	deleteApiKey(id: string): Promise<void>;
	rotateApiKey(id: string, newKey: string): Promise<ApiKey>;

	subscribeSSE(callback: (event: SSEEvent) => void): () => void;
}

// --- Helpers ---

function toTarget(o: any): Target {
	return {
		id: String(o.id),
		name: o.name,
		type: (o.type as Target['type']) ?? 'domain',
		status: (o.status as Target['status']) ?? 'active',
		lastSeen: o.last_seen,
		tags: o.tags ?? [],
		createdAt: o.created_at ?? o.createdAt,
		updatedAt: o.updated_at ?? o.updatedAt,
		recordCount: o.record_count ?? o.recordCount ?? 0,
		taskCount: o.task_count ?? o.taskCount ?? 0,
	};
}

function toTask(o: any): Task {
	return {
		id: String(o.id),
		name: o.name,
		type: (o.engine ?? o.type) as Task['type'],
		status: (o.status as Task['status']) ?? 'pending',
		targetId: String(o.target_id) ?? String(o.targetId),
		createdAt: o.created_at ?? o.createdAt,
		updatedAt: o.updated_at ?? o.updatedAt,
		startedAt: o.started_at ?? o.startedAt,
		completedAt: o.completed_at ?? o.completedAt,
		progress: o.progress ?? 0,
		recordsCount: o.records_count ?? o.recordsCount ?? 0,
		recipeId: o.recipe_id ?? o.recipeId,
		error: o.error_message ?? o.error,
		result: o.result ?? o.resultData,
	};
}

// Convert backend Record to frontend Result
function toResult(o: any): Result {
	// Map severity from confidence or metadata
	let severity: Result['severity'] = 'info';
	if (typeof o.confidence === 'number') {
		if (o.confidence >= 0.9) severity = 'critical';
		else if (o.confidence >= 0.7) severity = 'high';
		else if (o.confidence >= 0.4) severity = 'warning';
		else severity = 'info';
	}

	// Map record type to result type
	const typeMap: Record<string, Result['type']> = {
		dns: 'dns-record',
		port: 'port-open',
		http: 'http-response',
		whois: 'whois',
		subdomain: 'subdomain',
		vulnerability: 'vuln',
		shodan: 'ip-lookup',
		virustotal: 'ip-lookup',
		generic: 'dns-record',
	};
	const type = typeMap[o.type] ?? 'dns-record';

	// Build message from data if not present
	let message = o.message;
	if (!message && o.data) {
		if (o.type === 'port') {
			message = `Port ${o.data.port ?? '?'}/${o.data.protocol ?? 'tcp'} OPEN (${o.data.service ?? 'unknown'})`;
		} else if (o.type === 'dns') {
			message = `${o.data.recordType ?? 'A'} record: ${o.data.name ?? '?'} → ${o.data.value ?? '?'}`;
		} else {
			message = `${o.type}: ${JSON.stringify(o.data).slice(0, 100)}`;
		}
	}

	// Target name from backend
	const target = o.target_name ?? o.target ?? o.target_name_from_record;

	return {
		id: String(o.id),
		taskId: String(o.task_id) ?? String(o.taskId),
		type,
		severity,
		message: message ?? `${o.type} from ${o.source}`,
		target: target ?? 'unknown',
		timestamp: o.timestamp ?? o.created_at ?? o.createdAt,
		data: o.data ?? {},
	};
}

function toApiKey(o: any): ApiKey {
	return {
		id: String(o.id),
		name: o.name,
		source: o.source,
		key: o.key,
		primary: o.primary ?? false,
		fallback: o.fallback ?? false,
		status: o.status ?? 'active',
		createdAt: o.created_at ?? o.createdAt,
		updatedAt: o.updated_at ?? o.updatedAt,
	};
}

// --- SSE ---

export function subscribeSSE(url: string, onEvent: (event: SSEEvent) => void): () => void {
	const es = new EventSource(url);

	const handler = (e: MessageEvent) => {
		try {
			const data = JSON.parse(e.data);
			onEvent(data as SSEEvent);
		} catch { /* ignore parse errors */ }
	};

	es.addEventListener('message', handler);

	return () => {
		es.removeEventListener('message', handler);
		es.close();
	};
}

// --- Real API ---

export const apiService: APIService = {
	async getTargets(): Promise<Target[]> {
		const data = await fetchJSON<any>('/targets');
		return data.map(toTarget);
	},

	async getTarget(id: string): Promise<Target | null> {
		const data = await fetchJSON<any>(`/targets/${id}`);
		return toTarget(data);
	},

	async createTarget(target: Omit<Target, 'id' | 'createdAt' | 'updatedAt'>): Promise<Target> {
		const data = await fetchJSON<any>('/targets', {
			method: 'POST',
			body: JSON.stringify(target),
		});
		return toTarget(data);
	},

	async updateTarget(id: string, updates: Partial<Target>): Promise<Target> {
		const data = await fetchJSON<any>(`/targets/${id}`, {
			method: 'PUT',
			body: JSON.stringify(updates),
		});
		return toTarget(data);
	},

	async deleteTarget(id: string): Promise<void> {
		await fetchJSON<void>(`/targets/${id}`, { method: 'DELETE' });
	},

	async getTasks(): Promise<Task[]> {
		const data = await fetchJSON<any>('/tasks');
		return data.map(toTask);
	},

	async getTask(id: string): Promise<Task | null> {
		const data = await fetchJSON<any>(`/tasks/${id}`);
		return toTask(data);
	},

	async createTask(task: Omit<Task, 'id' | 'createdAt' | 'updatedAt' | 'progress' | 'recordsCount'>): Promise<Task> {
		const data = await fetchJSON<any>('/tasks', {
			method: 'POST',
			body: JSON.stringify(task),
		});
		return toTask(data);
	},

	async updateTask(id: string, updates: Partial<Task>): Promise<Task> {
		const data = await fetchJSON<any>(`/tasks/${id}`, {
			method: 'PUT',
			body: JSON.stringify(updates),
		});
		return toTask(data);
	},

	async deleteTask(id: string): Promise<void> {
		await fetchJSON<void>(`/tasks/${id}`, { method: 'DELETE' });
	},

	async startTask(id: string): Promise<Task> {
		const data = await fetchJSON<any>(`/tasks/${id}/start`, { method: 'POST' });
		return toTask(data);
	},

	async cancelTask(id: string): Promise<Task> {
		const data = await fetchJSON<any>(`/tasks/${id}/cancel`, { method: 'POST' });
		return toTask(data);
	},

	async getResults(): Promise<Result[]> {
		const data = await fetchJSON<any>('/records');
		return data.map(toResult);
	},

	async getResultsByTask(taskId: string): Promise<Result[]> {
		const data = await fetchJSON<any>(`/records?target_id=${taskId}`);
		return data.map(toResult);
	},

	async getResult(id: string): Promise<Result | null> {
		const data = await fetchJSON<any>(`/records/${id}`);
		return toResult(data);
	},

	// API Keys
	async getApiKeys(): Promise<ApiKey[]> {
		const data = await fetchJSON<any>('/api-keys');
		return data.map(toApiKey);
	},

	async getApiKey(id: string): Promise<ApiKey | null> {
		const data = await fetchJSON<any>(`/api-keys/${id}`);
		return toApiKey(data);
	},

	async createApiKey(apiKey: Omit<ApiKey, 'id' | 'createdAt' | 'updatedAt' | 'status'>): Promise<ApiKey> {
		const data = await fetchJSON<any>('/api-keys', {
			method: 'POST',
			body: JSON.stringify(apiKey),
		});
		return toApiKey(data);
	},

	async updateApiKey(id: string, updates: Partial<ApiKey>): Promise<ApiKey> {
		const data = await fetchJSON<any>(`/api-keys/${id}`, {
			method: 'PUT',
			body: JSON.stringify(updates),
		});
		return toApiKey(data);
	},

	async deleteApiKey(id: string): Promise<void> {
		await fetchJSON<void>(`/api-keys/${id}`, { method: 'DELETE' });
	},

	async rotateApiKey(id: string, newKey: string): Promise<ApiKey> {
		const data = await fetchJSON<any>(`/api-keys/${id}/rotate`, {
			method: 'PUT',
			body: JSON.stringify({ new_key: newKey }),
		});
		return toApiKey(data);
	},

	// SSE — subscribe to a single task's SSE stream
	subscribeSSEForTask(taskId: string, callback: (event: SSEEvent) => void): () => void {
		const url = `${BASE}/tasks/${taskId}/stream`;
		return subscribeSSE(url, callback);
	},
};
