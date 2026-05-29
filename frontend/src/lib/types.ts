/**
 * Core domain types for OSINTote.
 */

// --- Target ---

export type TargetType = 'domain' | 'hostname' | 'ip' | 'cidr' | 'email' | 'url';

export interface Target {
	id: string;
	name: string;
	type: TargetType;
	status: 'active' | 'inactive' | 'idle';
	lastSeen?: string;
	tags: string[];
	createdAt: string;
	updatedAt: string;
	recordCount?: number;
	taskCount?: number;
}

// --- Task ---

export type TaskType = 'dns-enumerate' | 'nmap' | 'whois' | 'http-probe' | 'subdomain' |
	'cert-scan' | 'vuln-scan' | 'api-scan' | 'custom';

export type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'canceled';

export interface Task {
	id: string;
	name: string;
	type: TaskType;
	status: TaskStatus;
	targetId: string;
	recipeId?: string;
	createdAt: string;
	updatedAt: string;
	startedAt?: string;
	completedAt?: string;
	progress: number;
	recordsCount: number;
	error?: string;
	result?: Record<string, unknown>;
}

// --- Result ---

export type Severity = 'info' | 'warning' | 'high' | 'critical';
export type RecordType = 'dns-record' | 'port-open' | 'http-response' | 'whois' |
	'subdomain' | 'cert' | 'vuln' | 'ip-lookup' | 'email-lookup';

export interface Result {
	id: string;
	taskId: string;
	type: RecordType;
	severity: Severity;
	message: string;
	target: string;
	timestamp: string;
	data: Record<string, unknown>;
}

// --- SSE Events ---

export type SSEEventType = 'task_started' | 'progress' | 'stage_complete' | 'task_finished' |
	'task_failed' | 'target_added' | 'target_updated' | 'result_created';

export interface SSEEvent {
	type: SSEEventType;
	taskId?: string;
	targetId?: string;
	resultId?: string;
	data?: Record<string, unknown>;
	timestamp: string;
}

// --- Logs ---

export interface LogEntry {
	timestamp: string;
	level: string;
	logger: string;
	message: string;
	pid?: number;
}

// --- API Keys ---

export type ApiKeyStatus = 'active' | 'rate-limited' | 'failed' | 'unknown';

export interface ApiKey {
	id: string;
	name: string;
	source: string;
	key: string;
	primary: boolean;
	fallback: boolean;
	status: ApiKeyStatus;
	createdAt: string;
	updatedAt: string;
}
