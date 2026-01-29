// src/hooks/useTaskPolling.ts
/**
 * Smart Task Polling Hook
 * =======================
 * 
 * This hook implements intelligent polling for task analysis status with:
 * - Exponential backoff to reduce server load
 * - Maximum retry limit to prevent infinite loops
 * - Total duration timeout for stuck tasks
 * - Automatic cleanup on unmount
 * 
 * The Infinite Loop Problem (SOLVED):
 * ------------------------------------
 * The original implementation used setInterval with a fixed interval and no
 * stop condition. If the backend never marked a task as prioritized (due to
 * an error, crash, or timeout), the polling would continue forever.
 * 
 * This implementation solves it by:
 * 1. Tracking polling attempts per task
 * 2. Using setTimeout instead of setInterval for exponential backoff
 * 3. Enforcing both maxAttempts AND maxDuration limits
 * 4. Transitioning to TIMED_OUT state when limits are exceeded
 * 
 * Exponential Backoff Math:
 * -------------------------
 * interval(n) = min(initialInterval × multiplier^(n-1), maxInterval)
 * 
 * With defaults (initial=2000ms, multiplier=2, max=10000ms):
 *   n=1: min(2000 × 2^0, 10000) = 2000ms
 *   n=2: min(2000 × 2^1, 10000) = 4000ms
 *   n=3: min(2000 × 2^2, 10000) = 8000ms
 *   n=4: min(2000 × 2^3, 10000) = 10000ms (capped)
 *   n=5+: 10000ms (stays capped)
 */

import { useCallback, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@/redux/store';
import {
    selectTasksNeedingPolling,
    updateTaskStatus,
    updateTaskFromServer,
    markTaskTimedOut,
    incrementPollingAttempt,
} from '@/redux/slices/tasksSlice';
import apiClient from '@/lib/apiClient';
import {
    Task,
    TaskAnalysisStatus,
    PollingConfig,
    DEFAULT_POLLING_CONFIG,
} from '@/types/tasks';

// ---------------------------------------------------------------------------
// TYPES
// ---------------------------------------------------------------------------

interface PollingState {
    /** Active timeout ID for cleanup */
    timeoutId: NodeJS.Timeout | null;
    
    /** Timestamp when polling started for this batch */
    startedAt: number;
    
    /** Set of task IDs currently being polled */
    activeTaskIds: Set<number>;
}

interface UseTaskPollingOptions {
    /** Custom polling configuration */
    config?: Partial<PollingConfig>;
    
    /** Whether polling is enabled */
    enabled?: boolean;
    
    /** Callback when a task completes */
    onTaskComplete?: (task: Task) => void;
    
    /** Callback when a task fails/times out */
    onTaskError?: (task: Task, error: string) => void;
}

interface UseTaskPollingReturn {
    /** Whether any tasks are currently being polled */
    isPolling: boolean;
    
    /** Number of tasks currently being polled */
    pollingCount: number;
    
    /** Manually trigger a poll cycle */
    pollNow: () => void;
    
    /** Retry a specific failed/timed-out task */
    retryTask: (taskId: number) => void;
}


// ---------------------------------------------------------------------------
// HELPER FUNCTIONS
// ---------------------------------------------------------------------------

/**
 * Calculate the next polling interval using exponential backoff.
 * 
 * @param attempt - Current attempt number (1-indexed)
 * @param config - Polling configuration
 * @returns Next interval in milliseconds
 */
function calculateBackoffInterval(
    attempt: number,
    config: PollingConfig
): number {
    // Formula: min(initial × multiplier^(attempt-1), maxInterval)
    const exponentialDelay = 
        config.initialInterval * Math.pow(config.backoffMultiplier, attempt - 1);
    
    return Math.min(exponentialDelay, config.maxInterval);
}

/**
 * Check if polling should stop for a specific task.
 * 
 * @param task - Task to check
 * @param config - Polling configuration
 * @param startedAt - Timestamp when polling batch started
 * @returns Object with shouldStop flag and reason
 */
function shouldStopPolling(
    task: Task,
    config: PollingConfig,
    startedAt: number
): { shouldStop: boolean; reason?: string } {
    // Check if task is already in terminal state
    if (task.is_prioritized) {
        return { shouldStop: true, reason: 'completed' };
    }
    
    if (task.analysisStatus === TaskAnalysisStatus.COMPLETED) {
        return { shouldStop: true, reason: 'completed' };
    }
    
    if (task.analysisStatus === TaskAnalysisStatus.FAILED) {
        return { shouldStop: true, reason: 'failed' };
    }
    
    if (task.analysisStatus === TaskAnalysisStatus.TIMED_OUT) {
        return { shouldStop: true, reason: 'timed_out' };
    }
    
    // Check max attempts
    const attempts = task.pollingAttempts ?? 0;
    if (attempts >= config.maxAttempts) {
        return { shouldStop: true, reason: 'max_attempts_exceeded' };
    }
    
    // Check max duration
    const elapsed = Date.now() - startedAt;
    if (elapsed >= config.maxDuration) {
        return { shouldStop: true, reason: 'max_duration_exceeded' };
    }
    
    return { shouldStop: false };
}


// ---------------------------------------------------------------------------
// MAIN HOOK
// ---------------------------------------------------------------------------

/**
 * Smart polling hook for task analysis status.
 * 
 * @param options - Configuration options
 * @returns Polling control interface
 */
export function useTaskPolling(
    options: UseTaskPollingOptions = {}
): UseTaskPollingReturn {
    const {
        config: customConfig,
        enabled = true,
        onTaskComplete,
        onTaskError,
    } = options;
    
    // Merge custom config with defaults
    const config: PollingConfig = {
        ...DEFAULT_POLLING_CONFIG,
        ...customConfig,
    };
    
    const dispatch = useDispatch<AppDispatch>();
    
    // Select tasks that need polling
    const tasksNeedingPolling = useSelector(selectTasksNeedingPolling);
    
    // Refs for cleanup and state tracking
    const pollingStateRef = useRef<PollingState>({
        timeoutId: null,
        startedAt: Date.now(),
        activeTaskIds: new Set(),
    });
    
    // Track if we're currently in a poll cycle
    const isPollingRef = useRef(false);
    
    /**
     * Execute a single poll cycle for all pending tasks.
     */
    const executePollCycle = useCallback(async () => {
        if (!enabled || tasksNeedingPolling.length === 0) {
            isPollingRef.current = false;
            return;
        }
        
        isPollingRef.current = true;
        const state = pollingStateRef.current;
        
        // Process each task that needs polling
        const pollPromises = tasksNeedingPolling.map(async (task) => {
            // Check if we should stop polling this task
            const { shouldStop, reason } = shouldStopPolling(task, config, state.startedAt);
            
            if (shouldStop) {
                state.activeTaskIds.delete(task.id);
                
                if (reason === 'max_attempts_exceeded' || reason === 'max_duration_exceeded') {
                    // Mark as timed out
                    dispatch(markTaskTimedOut(task.id));
                    onTaskError?.(task, `Polling ${reason.replace(/_/g, ' ')}`);
                }
                
                return;
            }
            
            // Add to active set
            state.activeTaskIds.add(task.id);
            
            try {
                // Increment attempt counter BEFORE the API call
                dispatch(incrementPollingAttempt(task.id));
                
                // Fetch latest task status from server
                const response = await apiClient.get<Task>(`/tasks/${task.id}/`);
                const serverTask = response.data;
                
                if (serverTask.is_prioritized) {
                    // Task completed on server!
                    dispatch(updateTaskFromServer(serverTask));
                    dispatch(updateTaskStatus({
                        taskId: task.id,
                        status: TaskAnalysisStatus.COMPLETED,
                    }));
                    state.activeTaskIds.delete(task.id);
                    onTaskComplete?.(serverTask);
                } else {
                    // Still processing - update status to ANALYZING if not already
                    if (task.analysisStatus !== TaskAnalysisStatus.ANALYZING) {
                        dispatch(updateTaskStatus({
                            taskId: task.id,
                            status: TaskAnalysisStatus.ANALYZING,
                        }));
                    }
                }
            } catch (error) {
                console.error(`Polling error for task ${task.id}:`, error);
                
                // Don't immediately fail - the task might still be processing
                // Just log and continue polling
            }
        });
        
        // Wait for all polls to complete
        await Promise.allSettled(pollPromises);
        
        // Schedule next poll cycle if there are still tasks to poll
        const remainingTasks = tasksNeedingPolling.filter(
            t => !shouldStopPolling(t, config, state.startedAt).shouldStop
        );
        
        if (remainingTasks.length > 0 && enabled) {
            // Calculate backoff based on the maximum attempts among remaining tasks
            const maxAttempts = Math.max(
                ...remainingTasks.map(t => (t.pollingAttempts ?? 0) + 1)
            );
            const nextInterval = calculateBackoffInterval(maxAttempts, config);
            
            // Schedule next cycle
            state.timeoutId = setTimeout(() => {
                executePollCycle();
            }, nextInterval);
        } else {
            isPollingRef.current = false;
        }
    }, [enabled, tasksNeedingPolling, config, dispatch, onTaskComplete, onTaskError]);
    
    /**
     * Manually trigger a poll cycle.
     */
    const pollNow = useCallback(() => {
        // Cancel any pending timeout
        if (pollingStateRef.current.timeoutId) {
            clearTimeout(pollingStateRef.current.timeoutId);
            pollingStateRef.current.timeoutId = null;
        }
        
        // Reset start time for fresh polling batch
        pollingStateRef.current.startedAt = Date.now();
        
        // Execute immediately
        executePollCycle();
    }, [executePollCycle]);
    
    /**
     * Retry a specific failed/timed-out task.
     */
    const retryTask = useCallback((taskId: number) => {
        // Reset the task's polling state
        dispatch(updateTaskStatus({
            taskId,
            status: TaskAnalysisStatus.PENDING,
            resetAttempts: true,
        }));
        
        // Reset start time and trigger poll
        pollingStateRef.current.startedAt = Date.now();
        
        // Trigger a poll cycle
        setTimeout(() => executePollCycle(), 100);
    }, [dispatch, executePollCycle]);
    
    // ---------------------------------------------------------------------------
    // EFFECTS
    // ---------------------------------------------------------------------------
    
    // Start/stop polling based on tasks needing it
    useEffect(() => {
        if (!enabled) {
            // Cleanup if disabled
            if (pollingStateRef.current.timeoutId) {
                clearTimeout(pollingStateRef.current.timeoutId);
                pollingStateRef.current.timeoutId = null;
            }
            return;
        }
        
        if (tasksNeedingPolling.length > 0 && !isPollingRef.current) {
            // Start polling for new tasks
            pollingStateRef.current.startedAt = Date.now();
            executePollCycle();
        }
    }, [enabled, tasksNeedingPolling.length, executePollCycle]);
    
    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (pollingStateRef.current.timeoutId) {
                clearTimeout(pollingStateRef.current.timeoutId);
                pollingStateRef.current.timeoutId = null;
            }
        };
    }, []);
    
    // ---------------------------------------------------------------------------
    // RETURN
    // ---------------------------------------------------------------------------
    
    return {
        isPolling: isPollingRef.current && tasksNeedingPolling.length > 0,
        pollingCount: tasksNeedingPolling.length,
        pollNow,
        retryTask,
    };
}

// Export default for backward compatibility
export default useTaskPolling;
