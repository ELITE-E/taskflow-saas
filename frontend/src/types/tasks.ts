// /src/types/tasks.ts
/**
 * Task Type Definitions
 * =====================
 * 
 * This module defines all TypeScript interfaces for the Task domain.
 * 
 * Status Flow:
 * ------------
 *   PENDING → ANALYZING → COMPLETED
 *                      ↘ FAILED
 *                      ↘ TIMED_OUT
 */

// ---------------------------------------------------------------------------
// ENUMS & CONSTANTS
// ---------------------------------------------------------------------------

/**
 * Task analysis status enum.
 * 
 * Represents the current state of AI prioritization processing.
 */
export enum TaskAnalysisStatus {
    /** Task created, waiting to be queued for AI analysis */
    PENDING = 'PENDING',
    
    /** Task is currently being processed by the AI engine */
    ANALYZING = 'ANALYZING',
    
    /** AI analysis completed successfully */
    COMPLETED = 'COMPLETED',
    
    /** AI analysis failed (API error, validation error, etc.) */
    FAILED = 'FAILED',
    
    /** Polling timed out - task may still be processing on server */
    TIMED_OUT = 'TIMED_OUT',
}

/**
 * Eisenhower Matrix quadrant identifiers.
 */
export type Quadrant = 'Q1' | 'Q2' | 'Q3' | 'Q4';

/**
 * Quadrant metadata for UI display.
 */
export interface QuadrantInfo {
    id: Quadrant;
    title: string;
    subtitle: string;
    description: string;
    color: string;
    priority: number;
}

/**
 * Quadrant configuration for the Eisenhower Matrix.
 */
export const QUADRANT_CONFIG: Record<Quadrant, QuadrantInfo> = {
    Q1: {
        id: 'Q1',
        title: 'DO NOW',
        subtitle: 'Urgent & Important',
        description: 'Critical tasks requiring immediate attention',
        color: '#fee2e2',
        priority: 1,
    },
    Q2: {
        id: 'Q2',
        title: 'SCHEDULE',
        subtitle: 'Not Urgent & Important',
        description: 'Strategic tasks to plan and execute',
        color: '#fef3c7',
        priority: 2,
    },
    Q3: {
        id: 'Q3',
        title: 'DELEGATE',
        subtitle: 'Urgent & Not Important',
        description: 'Tasks that can be delegated or minimized',
        color: '#dcfce7',
        priority: 3,
    },
    Q4: {
        id: 'Q4',
        title: 'DELETE / DROP',
        subtitle: 'Not Urgent & Not Important',
        description: 'Consider eliminating these tasks',
        color: '#f3f4f6',
        priority: 4,
    },
};


// ---------------------------------------------------------------------------
// CORE INTERFACES
// ---------------------------------------------------------------------------

/**
 * Main Task interface representing a task entity.
 * 
 * This interface aligns with the Django Task model on the backend.
 */
export interface Task {
    /** Unique identifier (negative for optimistic/temporary tasks) */
    id: number;
    
    /** User ID who owns this task */
    user: number;
    
    /** User's email address */
    user_email: string;
    
    /** Task title (required) */
    title: string;
    
    /** Detailed task description */
    description: string;
    
    /** Due date in ISO format (YYYY-MM-DD) or null */
    due_date: string | null;
    
    /** Effort estimate on 1-5 scale */
    effort_estimate: number;
    
    /** Whether task has been marked complete */
    is_completed: boolean;
    
    /** Creation timestamp (ISO format) */
    created_at: string;
    
    /** Last update timestamp (ISO format) */
    updated_at: string;
    
    /** AI-calculated priority score [0-1] */
    priority_score: number;
    
    /** Associated goal ID (optional) */
    goal: number | null;
    
    /** Weight of associated goal (optional) */
    goal_weight: number | null;
    
    /** Legacy flag - use analysisStatus instead for granular tracking */
    is_prioritized: boolean;
    
    /** Celery task ID for background processing */
    async_status_id?: string;
    
    /** Eisenhower Matrix quadrant assignment */
    quadrant?: Quadrant;
    
    /** AI-calculated importance score [0-1] */
    importance_score?: number;
    
    /** AI-calculated urgency score [0-1] */
    urgency_score?: number;
    
    /** Human-readable explanation of prioritization */
    rationale?: string;
    
    // ----- CLIENT-SIDE ONLY FIELDS -----
    // These are managed by Redux and not sent to/from the server
    
    /** Current analysis status (client-side tracking) */
    analysisStatus?: TaskAnalysisStatus;
    
    /** Number of polling attempts made (client-side tracking) */
    pollingAttempts?: number;
    
    /** Error message if analysis failed (client-side tracking) */
    analysisError?: string;
    
    /** Timestamp when analysis started (client-side tracking) */
    analysisStartedAt?: string;
}


// ---------------------------------------------------------------------------
// API PAYLOAD INTERFACES
// ---------------------------------------------------------------------------

/**
 * Payload for creating or updating a task.
 */
export interface TaskPayload {
    title: string;
    description?: string;
    due_date?: string | null;
    effort_estimate?: number;
    is_completed?: boolean;
    goal?: number | null;
}

/**
 * Response from the task status check endpoint.
 */
export interface TaskStatusResponse {
    id: number;
    is_prioritized: boolean;
    quadrant?: Quadrant;
    importance_score?: number;
    urgency_score?: number;
    rationale?: string;
}


// ---------------------------------------------------------------------------
// POLLING CONFIGURATION
// ---------------------------------------------------------------------------

/**
 * Configuration for the smart polling system.
 */
export interface PollingConfig {
    /** Initial polling interval in milliseconds */
    initialInterval: number;
    
    /** Maximum polling interval in milliseconds */
    maxInterval: number;
    
    /** Backoff multiplier (interval grows by this factor) */
    backoffMultiplier: number;
    
    /** Maximum number of polling attempts before timeout */
    maxAttempts: number;
    
    /** Maximum total polling duration in milliseconds */
    maxDuration: number;
}

/**
 * Default polling configuration.
 * 
 * Exponential backoff schedule:
 *   Attempt 1: 2000ms
 *   Attempt 2: 2000ms (min)
 *   Attempt 3: 4000ms
 *   Attempt 4: 8000ms
 *   Attempt 5: 10000ms (capped at max)
 *   ...continues at 10000ms until maxAttempts or maxDuration
 */
export const DEFAULT_POLLING_CONFIG: PollingConfig = {
    initialInterval: 2000,      // Start at 2 seconds
    maxInterval: 10000,         // Cap at 10 seconds
    backoffMultiplier: 2,       // Double each time
    maxAttempts: 15,            // Max 15 attempts
    maxDuration: 45000,         // Max 45 seconds total
};


// ---------------------------------------------------------------------------
// GROUPED TASKS INTERFACE
// ---------------------------------------------------------------------------

/**
 * Tasks grouped by quadrant for matrix display.
 */
export interface GroupedTasks {
    Q1: Task[];
    Q2: Task[];
    Q3: Task[];
    Q4: Task[];
}

/**
 * Tasks grouped by analysis status.
 */
export interface TasksByStatus {
    pending: Task[];
    analyzing: Task[];
    completed: Task[];
    failed: Task[];
    timedOut: Task[];
}


// ---------------------------------------------------------------------------
// UTILITY TYPE GUARDS
// ---------------------------------------------------------------------------

/**
 * Check if a task is in a terminal state (no longer processing).
 */
export function isTaskTerminal(task: Task): boolean {
    const status = task.analysisStatus;
    return (
        status === TaskAnalysisStatus.COMPLETED ||
        status === TaskAnalysisStatus.FAILED ||
        status === TaskAnalysisStatus.TIMED_OUT ||
        task.is_prioritized
    );
}

/**
 * Check if a task needs polling (still processing).
 */
export function needsPolling(task: Task): boolean {
    // Optimistic tasks (negative ID) need polling once they get real ID
    if (task.id < 0) return false;
    
    const status = task.analysisStatus;
    return (
        status === TaskAnalysisStatus.PENDING ||
        status === TaskAnalysisStatus.ANALYZING ||
        (!task.is_prioritized && !status)
    );
}

/**
 * Get display-friendly status label.
 */
export function getStatusLabel(status: TaskAnalysisStatus | undefined): string {
    switch (status) {
        case TaskAnalysisStatus.PENDING:
            return 'Waiting...';
        case TaskAnalysisStatus.ANALYZING:
            return 'AI is thinking...';
        case TaskAnalysisStatus.COMPLETED:
            return 'Prioritized';
        case TaskAnalysisStatus.FAILED:
            return 'Failed';
        case TaskAnalysisStatus.TIMED_OUT:
            return 'Timed out';
        default:
            return 'Unknown';
    }
}
