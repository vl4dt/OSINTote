/**
 * Mock API service for OSINTote frontend development.
 * Provides realistic data and simulated SSE events.
 * Swap for real API endpoints when backend is ready.
 */

import type { ApiKey, Target, Task, TaskStatus, Result, SSEEvent } from '$lib/types';

// --- Seed Data ---

export const mockTargets: Target[] = [
	{
		id: 'tgt-001',
		name: 'example.com',
		type: 'domain',
		status: 'active',
		lastSeen: '2026-05-28 14:32:00',
		tags: ['web', 'production'],
		createdAt: '2026-05-20 10:00:00',
		updatedAt: '2026-05-28 14:32:00',
		recordCount: 47,
		taskCount: 12
	},
	{
		id: 'tgt-002',
		name: 'api.service.dev',
		type: 'hostname',
		status: 'active',
		lastSeen: '2026-05-28 12:15:00',
		tags: ['api', 'staging'],
		createdAt: '2026-05-22 08:30:00',
		updatedAt: '2026-05-28 12:15:00',
		recordCount: 23,
		taskCount: 5
	},
	{
		id: 'tgt-003',
		name: '192.168.1.0/24',
		type: 'cidr',
		status: 'idle',
		lastSeen: '2026-05-27 09:45:00',
		tags: ['internal', 'network'],
		createdAt: '2026-05-15 16:00:00',
		updatedAt: '2026-05-27 09:45:00',
		recordCount: 156,
		taskCount: 28
	},
	{
		id: 'tgt-004',
		name: 'malicious-domain.xyz',
		type: 'domain',
		status: 'inactive',
		lastSeen: '2026-05-25 18:20:00',
		tags: ['threat', 'blocked'],
		createdAt: '2026-05-10 09:00:00',
		updatedAt: '2026-05-25 18:20:00',
		recordCount: 8,
		taskCount: 3
	},
	{
		id: 'tgt-005',
		name: '10.0.0.50',
		type: 'ip',
		status: 'active',
		lastSeen: '2026-05-28 15:00:00',
		tags: ['server', 'database'],
		createdAt: '2026-05-25 11:00:00',
		updatedAt: '2026-05-28 15:00:00',
		recordCount: 31,
		taskCount: 7
	},
	{
		id: 'tgt-006',
		name: 'admin.panel.corp.local',
		type: 'hostname',
		status: 'idle',
		lastSeen: '2026-05-26 07:30:00',
		tags: ['internal', 'admin'],
		createdAt: '2026-05-18 14:00:00',
		updatedAt: '2026-05-26 07:30:00',
		recordCount: 5,
		taskCount: 2
	}
];

export const mockTasks: Task[] = [
	{
		id: 'tsk-001',
		name: 'Port scan: example.com',
		type: 'nmap',
		status: 'running',
		targetId: 'tgt-001',
		createdAt: '2026-05-28 14:30:00',
		updatedAt: '2026-05-28 14:35:00',
		startedAt: '2026-05-28 14:30:15',
		progress: 65,
		recordsCount: 23,
		recipeId: 'full-scan'
	},
	{
		id: 'tsk-002',
		name: 'DNS enumeration: api.service.dev',
		type: 'dns-enumerate',
		status: 'completed',
		targetId: 'tgt-002',
		createdAt: '2026-05-28 12:10:00',
		updatedAt: '2026-05-28 12:15:30',
		startedAt: '2026-05-28 12:10:05',
		completedAt: '2026-05-28 12:15:30',
		progress: 100,
		recordsCount: 18
	},
	{
		id: 'tsk-003',
		name: 'Subdomain brute force: internal.net',
		type: 'subdomain',
		status: 'failed',
		targetId: 'tgt-003',
		createdAt: '2026-05-27 09:40:00',
		updatedAt: '2026-05-27 10:12:00',
		startedAt: '2026-05-27 09:40:30',
		progress: 34,
		recordsCount: 7,
		error: 'Connection timeout after 1800s'
	},
	{
		id: 'tsk-004',
		name: 'WHOIS lookup: malicious-domain.xyz',
		type: 'whois',
		status: 'completed',
		targetId: 'tgt-004',
		createdAt: '2026-05-25 18:15:00',
		updatedAt: '2026-05-25 18:16:00',
		startedAt: '2026-05-25 18:15:10',
		completedAt: '2026-05-25 18:16:00',
		progress: 100,
		recordsCount: 4
	},
	{
		id: 'tsk-005',
		name: 'Certificate scan: example.com',
		type: 'cert-scan',
		status: 'pending',
		targetId: 'tgt-001',
		createdAt: '2026-05-28 15:00:00',
		updatedAt: '2026-05-28 15:00:00',
		progress: 0,
		recordsCount: 0,
		recipeId: 'quick-scan'
	},
	{
		id: 'tsk-006',
		name: 'HTTP probe: api.service.dev',
		type: 'http-probe',
		status: 'queued',
		targetId: 'tgt-002',
		createdAt: '2026-05-28 15:05:00',
		updatedAt: '2026-05-28 15:05:00',
		progress: 0,
		recordsCount: 0
	},
	{
		id: 'tsk-007',
		name: 'Vuln scan: 10.0.0.50',
		type: 'vuln-scan',
		status: 'running',
		targetId: 'tgt-005',
		createdAt: '2026-05-28 13:00:00',
		updatedAt: '2026-05-28 14:40:00',
		startedAt: '2026-05-28 13:00:20',
		progress: 89,
		recordsCount: 42,
		recipeId: 'vuln-full'
	},
	{
		id: 'tsk-008',
		name: 'Nmap scan: 192.168.1.0/24',
		type: 'nmap',
		status: 'canceled',
		targetId: 'tgt-003',
		createdAt: '2026-05-26 10:00:00',
		updatedAt: '2026-05-26 10:30:00',
		startedAt: '2026-05-26 10:00:15',
		progress: 12,
		recordsCount: 3,
		error: 'User canceled'
	}
];

// --- API Keys ---

export const mockApiKeys: ApiKey[] = [
	{
		id: 'key-001',
		name: 'Shodan Primary',
		source: 'shodan',
		key: 'shodan-key-abc123',
		primary: true,
		fallback: false,
		status: 'active',
		createdAt: '2026-05-20 10:00:00',
		updatedAt: '2026-05-28 14:00:00',
	},
	{
		id: 'key-002',
		name: 'VirusTotal Primary',
		source: 'virustotal',
		key: 'vt-key-def456',
		primary: true,
		fallback: false,
		status: 'active',
		createdAt: '2026-05-22 08:30:00',
		updatedAt: '2026-05-28 12:15:00',
	},
	{
		id: 'key-003',
		name: 'Shodan Fallback',
		source: 'shodan',
		key: 'shodan-key-ghi789',
		primary: false,
		fallback: true,
		status: 'active',
		createdAt: '2026-05-23 09:00:00',
		updatedAt: '2026-05-27 09:45:00',
	},
	{
		id: 'key-004',
		name: 'OpenAI API',
		source: 'openai',
		key: 'sk-openai-xyz',
		primary: true,
		fallback: false,
		status: 'rate-limited',
		createdAt: '2026-05-25 11:00:00',
		updatedAt: '2026-05-28 15:00:00',
	},
];

export const mockResults: Result[] = [
	{
		id: 'res-001',
		taskId: 'tsk-001',
		type: 'port-open',
		severity: 'info',
		message: 'Port 80/tcp OPEN (HTTP - nginx/1.24.0)',
		target: 'example.com',
		timestamp: '2026-05-28 14:32:15',
		data: { port: 80, protocol: 'tcp', service: 'http', version: 'nginx/1.24.0' }
	},
	{
		id: 'res-002',
		taskId: 'tsk-001',
		type: 'port-open',
		severity: 'info',
		message: 'Port 443/tcp OPEN (HTTPS - nginx/1.24.0)',
		target: 'example.com',
		timestamp: '2026-05-28 14:32:16',
		data: { port: 443, protocol: 'tcp', service: 'https', version: 'nginx/1.24.0' }
	},
	{
		id: 'res-003',
		taskId: 'tsk-001',
		type: 'port-open',
		severity: 'critical',
		message: 'Port 22/tcp OPEN (SSH - OpenSSH_9.2p1)',
		target: 'example.com',
		timestamp: '2026-05-28 14:32:17',
		data: { port: 22, protocol: 'tcp', service: 'ssh', version: 'OpenSSH_9.2p1' }
	},
	{
		id: 'res-004',
		taskId: 'tsk-001',
		type: 'port-open',
		severity: 'warning',
		message: 'Port 3306/tcp OPEN (MySQL - 8.0.35)',
		target: 'example.com',
		timestamp: '2026-05-28 14:32:18',
		data: { port: 3306, protocol: 'tcp', service: 'mysql', version: '8.0.35' }
	},
	{
		id: 'res-005',
		taskId: 'tsk-002',
		type: 'dns-record',
		severity: 'info',
		message: 'A record: api.service.dev → 10.0.0.50 (TTL: 3600)',
		target: 'api.service.dev',
		timestamp: '2026-05-28 12:15:30',
		data: { recordType: 'A', value: '10.0.0.50', ttl: 3600 }
	},
	{
		id: 'res-006',
		taskId: 'tsk-002',
		type: 'dns-record',
		severity: 'info',
		message: 'MX record: api.service.dev → mail.service.dev (Priority: 10)',
		target: 'api.service.dev',
		timestamp: '2026-05-28 12:15:31',
		data: { recordType: 'MX', value: 'mail.service.dev', priority: 10 }
	},
	{
		id: 'res-007',
		taskId: 'tsk-002',
		type: 'dns-record',
		severity: 'info',
		message: 'NS record: api.service.dev → ns1.provider.com',
		target: 'api.service.dev',
		timestamp: '2026-05-28 12:15:32',
		data: { recordType: 'NS', value: 'ns1.provider.com' }
	},
	{
		id: 'res-008',
		taskId: 'tsk-007',
		type: 'vuln',
		severity: 'critical',
		message: 'CVE-2025-1234: Remote code execution in Apache Log4j',
		target: '10.0.0.50',
		timestamp: '2026-05-28 14:30:00',
		data: { cve: 'CVE-2025-1234', cvss: 9.8, affected: 'log4j 2.14.1' }
	},
	{
		id: 'res-009',
		taskId: 'tsk-007',
		type: 'vuln',
		severity: 'high',
		message: 'CVE-2025-5678: SQL injection in Spring Framework',
		target: '10.0.0.50',
		timestamp: '2026-05-28 14:28:00',
		data: { cve: 'CVE-2025-5678', cvss: 7.5, affected: 'spring-boot 2.7.0' }
	},
	{
		id: 'res-010',
		taskId: 'tsk-007',
		type: 'subdomain',
		severity: 'info',
		message: 'Discovered subdomain: db.internal.corp.local',
		target: '10.0.0.50',
		timestamp: '2026-05-28 14:20:00',
		data: { subdomain: 'db.internal.corp.local', resolution: '10.0.0.100' }
	}
];

// --- Simulated SSE Events ---

function generateSSEEvents(): SSEEvent[] {
	return [
		{
			type: 'task_started',
			taskId: 'tsk-001',
			timestamp: '2026-05-28 14:30:15'
		},
		{
			type: 'progress',
			taskId: 'tsk-001',
			data: { progress: 25 },
			timestamp: '2026-05-28 14:31:00'
		},
		{
			type: 'stage_complete',
			taskId: 'tsk-001',
			data: { stage: 'port-scan' },
			timestamp: '2026-05-28 14:32:00'
		},
		{
			type: 'progress',
			taskId: 'tsk-001',
			data: { progress: 65 },
			timestamp: '2026-05-28 14:33:30'
		},
		{
			type: 'progress',
			taskId: 'tsk-001',
			data: { progress: 100 },
			timestamp: '2026-05-28 14:34:00'
		},
		{
			type: 'task_finished',
			taskId: 'tsk-001',
			data: { recordsCount: 23 },
			timestamp: '2026-05-28 14:34:30'
		},
		{
			type: 'result_created',
			resultId: 'res-001',
			taskId: 'tsk-001',
			timestamp: '2026-05-28 14:32:15'
		},
		{
			type: 'target_added',
			targetId: 'tgt-new-1',
			timestamp: '2026-05-28 15:00:00'
		}
	];
}

// --- API Service ---

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

	// API Keys
	getApiKeys(): Promise<ApiKey[]>;
	getApiKey(id: string): Promise<ApiKey | null>;
	createApiKey(apiKey: Omit<ApiKey, 'id' | 'createdAt' | 'updatedAt' | 'status'>): Promise<ApiKey>;
	updateApiKey(id: string, updates: Partial<ApiKey>): Promise<ApiKey>;
	deleteApiKey(id: string): Promise<void>;
	rotateApiKey(id: string, newKey: string): Promise<ApiKey>;

	subscribeSSE(callback: (event: SSEEvent) => void): () => void;
}

export const mockAPIService: APIService = {
	async getTargets(): Promise<Target[]> {
		return Promise.resolve([...mockTargets]);
	},

	async getTarget(id: string): Promise<Target | null> {
		return Promise.resolve(mockTargets.find(t => t.id === id) ?? null);
	},

	async createTarget(data): Promise<Target> {
		const newTarget: Target = {
			...data,
			id: `tgt-${Date.now()}`,
			createdAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
			updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19)
		};
		mockTargets.push(newTarget);
		return Promise.resolve(newTarget);
	},

	async updateTarget(id, updates): Promise<Target> {
		const idx = mockTargets.findIndex(t => t.id === id);
		if (idx === -1) return Promise.resolve(null as any);
		Object.assign(mockTargets[idx], updates, { updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) });
		return Promise.resolve(mockTargets[idx]);
	},

	async deleteTarget(id): Promise<void> {
		const idx = mockTargets.findIndex(t => t.id === id);
		if (idx !== -1) mockTargets.splice(idx, 1);
		return Promise.resolve();
	},

	async getTasks(): Promise<Task[]> {
		return Promise.resolve([...mockTasks]);
	},

	async getTask(id: string): Promise<Task | null> {
		return Promise.resolve(mockTasks.find(t => t.id === id) ?? null);
	},

	async createTask(data): Promise<Task> {
		const newTask: Task = {
			...data,
			id: `tsk-${Date.now()}`,
			createdAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
			updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
			progress: 0,
			recordsCount: 0
		};
		mockTasks.push(newTask);
		return Promise.resolve(newTask);
	},

	async updateTask(id, updates): Promise<Task> {
		const idx = mockTasks.findIndex(t => t.id === id);
		if (idx === -1) return Promise.resolve(null as any);
		Object.assign(mockTasks[idx], updates, { updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) });
		return Promise.resolve(mockTasks[idx]);
	},

	async deleteTask(id): Promise<void> {
		const idx = mockTasks.findIndex(t => t.id === id);
		if (idx !== -1) mockTasks.splice(idx, 1);
		return Promise.resolve();
	},

	async startTask(id): Promise<Task> {
		const task = mockTasks.find(t => t.id === id);
		if (!task) return Promise.resolve(null as any);
		task.status = 'running' as TaskStatus;
		task.startedAt = new Date().toISOString().replace('T', ' ').slice(0, 19);
		task.updatedAt = new Date().toISOString().replace('T', ' ').slice(0, 19);
		task.progress = Math.max(task.progress, 5);
		return Promise.resolve(task);
	},

	async cancelTask(id): Promise<Task> {
		const task = mockTasks.find(t => t.id === id);
		if (!task) return Promise.resolve(null as any);
		task.status = 'canceled' as TaskStatus;
		task.updatedAt = new Date().toISOString().replace('T', ' ').slice(0, 19);
		task.error = 'User canceled';
		return Promise.resolve(task);
	},

	async getResults(): Promise<Result[]> {
		return Promise.resolve([...mockResults]);
	},

	async getResultsByTask(taskId: string): Promise<Result[]> {
		return Promise.resolve(mockResults.filter(r => r.taskId === taskId));
	},

	async getResult(id): Promise<Result | null> {
		return Promise.resolve(mockResults.find(r => r.id === id) ?? null);
	},

	// API Keys
	async getApiKeys(): Promise<ApiKey[]> {
		return Promise.resolve([...mockApiKeys]);
	},

	async getApiKey(id: string): Promise<ApiKey | null> {
		return Promise.resolve(mockApiKeys.find(k => k.id === id) ?? null);
	},

	async createApiKey(data): Promise<ApiKey> {
		const newKey: ApiKey = {
			...data,
			id: `key-${Date.now()}`,
			createdAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
			updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
			status: 'active',
		};
		mockApiKeys.push(newKey);
		return Promise.resolve(newKey);
	},

	async updateApiKey(id, updates): Promise<ApiKey> {
		const idx = mockApiKeys.findIndex(k => k.id === id);
		if (idx === -1) return Promise.resolve(null as any);
		Object.assign(mockApiKeys[idx], updates, { updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) });
		return Promise.resolve(mockApiKeys[idx]);
	},

	async deleteApiKey(id): Promise<void> {
		const idx = mockApiKeys.findIndex(k => k.id === id);
		if (idx !== -1) mockApiKeys.splice(idx, 1);
		return Promise.resolve();
	},

	async rotateApiKey(id, newKey): Promise<ApiKey> {
		const idx = mockApiKeys.findIndex(k => k.id === id);
		if (idx === -1) return Promise.resolve(null as any);
		mockApiKeys[idx] = {
			...mockApiKeys[idx],
			key: newKey,
			primary: true,
			updatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
		};
		return Promise.resolve(mockApiKeys[idx]);
	},

	subscribeSSE(callback: (event: SSEEvent) => void): () => void {
		const events = generateSSEEvents();
		let i = 0;

		function sendNext() {
			if (i >= events.length) return;
			callback(events[i]);
			i++;
			setTimeout(sendNext, 2000 + Math.random() * 3000);
		}

		// Start after a short delay
		setTimeout(sendNext, 1000);

		// Return unsubscribe function
		return () => { /* cleanup in real impl */ };
	}
};

// Export for development; production would import from './real.ts'
export const apiService = mockAPIService;
