// /src/redux/slices/tasksSlice.ts
/**
 * Tasks Redux Slice
 * =================
 * 
 * Manages the global state for tasks including:
 * - CRUD operations via async thunks
 * - Analysis status tracking
 * - Optimistic updates for snappy UX
 * - Polling state management
 * 
 * State Flow:
 * -----------
 *   addTask.pending  → Task added with PENDING status
 *   addTask.fulfilled → Task updated with server data, still PENDING
 *   polling detects → Status changes to ANALYZING
 *   server confirms → Status changes to COMPLETED
 *   timeout/error   → Status changes to FAILED or TIMED_OUT
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import {
    Task,
    TaskPayload,
    TaskAnalysisStatus,
    Quadrant,
    needsPolling,
    isTaskTerminal,
} from '@/types/tasks';
import * as tasksApi from '@/lib/tasks-api';
import { RootState } from '../store';

// ---------------------------------------------------------------------------
// STATE INTERFACE
// ---------------------------------------------------------------------------

interface TasksState {
    /** All tasks for the current user */
    tasks: Task[];
    
    /** Global loading state for fetch operations */
    loading: boolean;
    
    /** Global error message */
    error: string | null;
    
    /** Whether initial data has been loaded */
    initialized: boolean;
    
    /** Timestamp of last successful fetch */
    lastFetchedAt: string | null;
}

const initialState: TasksState = {
    tasks: [],
    loading: false,
    error: null,
    initialized: false,
    lastFetchedAt: null,
};


// ---------------------------------------------------------------------------
// ASYNC THUNKS
// ---------------------------------------------------------------------------

/**
 * Fetch all prioritized tasks from the server.
 */
export const getPrioritizedTasks = createAsyncThunk<Task[], void>(
    'tasks/getPrioritizedTasks',
    async (_, { rejectWithValue }) => {
        try {
            return await tasksApi.fetchPrioritizedTasks();
        } catch (error: any) {
            return rejectWithValue(
                error.response?.data?.detail || 'Failed to fetch tasks.'
            );
        }
    }
);

/**
 * Create a new task.
 * 
 * The task is immediately added to state with PENDING status (optimistic update).
 * Once the server responds, it's updated with the real ID.
 */
export const addTask = createAsyncThunk<Task, TaskPayload>(
    'tasks/addTask',
    async (payload, { rejectWithValue }) => {
        try {
            return await tasksApi.createTask(payload);
        } catch (error: any) {
            return rejectWithValue(
                error.response?.data || 'Failed to create task.'
            );
        }
    }
);

/**
 * Mark a task as completed.
 */
export const completeTask = createAsyncThunk<Task, number>(
    'tasks/completeTask',
    async (taskId, { rejectWithValue }) => {
        try {
            return await tasksApi.updateTask(taskId, { is_completed: true });
        } catch (error: any) {
            return rejectWithValue(
                error.response?.data || 'Failed to complete task.'
            );
        }
    }
);

/**
 * Delete a task permanently.
 */
export const removeTask = createAsyncThunk<number, number>(
    'tasks/removeTask',
    async (taskId, { rejectWithValue }) => {
        try {
            await tasksApi.deleteTask(taskId);
            return taskId;
        } catch (error: any) {
            return rejectWithValue(
                error.response?.data?.detail || 'Failed to delete task.'
            );
        }
    }
);

/**
 * Retry prioritization for a failed/timed-out task.
 */
export const retryTaskPrioritization = createAsyncThunk<Task, number>(
    'tasks/retryPrioritization',
    async (taskId, { rejectWithValue }) => {
        try {
            // Trigger re-analysis on the server
            const response = await tasksApi.updateTask(taskId, {});
            return response;
        } catch (error: any) {
            return rejectWithValue(
                error.response?.data || 'Failed to retry prioritization.'
            );
        }
    }
);


// ---------------------------------------------------------------------------
// SLICE DEFINITION
// ---------------------------------------------------------------------------

const tasksSlice = createSlice({
    name: 'tasks',
    initialState,
    
    reducers: {
        /**
         * Remove a task from local state only (no API call).
         * Useful for optimistic deletions.
         */
        removeTaskLocally: (state, action: PayloadAction<number>) => {
            state.tasks = state.tasks.filter(task => task.id !== action.payload);
        },
        
        /**
         * Update a task's analysis status.
         */
        updateTaskStatus: (
            state,
            action: PayloadAction<{
                taskId: number;
                status: TaskAnalysisStatus;
                error?: string;
                resetAttempts?: boolean;
            }>
        ) => {
            const { taskId, status, error, resetAttempts } = action.payload;
            const task = state.tasks.find(t => t.id === taskId);
            
            if (task) {
                task.analysisStatus = status;
                
                if (error) {
                    task.analysisError = error;
                }
                
                if (resetAttempts) {
                    task.pollingAttempts = 0;
                    task.analysisStartedAt = new Date().toISOString();
                }
                
                // If completing, also set is_prioritized for backward compatibility
                if (status === TaskAnalysisStatus.COMPLETED) {
                    task.is_prioritized = true;
                }
            }
        },
        
        /**
         * Update a task with fresh data from the server.
         */
        updateTaskFromServer: (state, action: PayloadAction<Task>) => {
            const serverTask = action.payload;
            const idx = state.tasks.findIndex(t => t.id === serverTask.id);
            
            if (idx !== -1) {
                // Preserve client-side tracking fields
                const existing = state.tasks[idx];
                state.tasks[idx] = {
                    ...serverTask,
                    analysisStatus: serverTask.is_prioritized
                        ? TaskAnalysisStatus.COMPLETED
                        : existing.analysisStatus,
                    pollingAttempts: existing.pollingAttempts,
                    analysisStartedAt: existing.analysisStartedAt,
                };
            }
        },
        
        /**
         * Increment the polling attempt counter for a task.
         */
        incrementPollingAttempt: (state, action: PayloadAction<number>) => {
            const task = state.tasks.find(t => t.id === action.payload);
            if (task) {
                task.pollingAttempts = (task.pollingAttempts ?? 0) + 1;
            }
        },
        
        /**
         * Mark a task as timed out from polling.
         */
        markTaskTimedOut: (state, action: PayloadAction<number>) => {
            const task = state.tasks.find(t => t.id === action.payload);
            if (task) {
                task.analysisStatus = TaskAnalysisStatus.TIMED_OUT;
                task.analysisError = 'Analysis timed out. The task may still be processing on the server.';
            }
        },
        
        /**
         * Mark a task as failed.
         */
        markTaskFailed: (
            state,
            action: PayloadAction<{ taskId: number; error: string }>
        ) => {
            const task = state.tasks.find(t => t.id === action.payload.taskId);
            if (task) {
                task.analysisStatus = TaskAnalysisStatus.FAILED;
                task.analysisError = action.payload.error;
            }
        },
        
        /**
         * Clear any global error state.
         */
        clearError: (state) => {
            state.error = null;
        },
        
        /**
         * Reset all task analysis states (useful for debugging).
         */
        resetAllAnalysisStates: (state) => {
            state.tasks.forEach(task => {
                if (!task.is_prioritized) {
                    task.analysisStatus = TaskAnalysisStatus.PENDING;
                    task.pollingAttempts = 0;
                    task.analysisError = undefined;
                }
            });
        },
    },
    
    extraReducers: (builder) => {
        builder
            // -----------------------------------------------------------------
            // GET PRIORITIZED TASKS
            // -----------------------------------------------------------------
            .addCase(getPrioritizedTasks.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(getPrioritizedTasks.fulfilled, (state, action: PayloadAction<Task[]>) => {
                state.loading = false;
                state.initialized = true;
                state.lastFetchedAt = new Date().toISOString();
                
                // Merge server tasks with existing client-side state
                const serverTasks = action.payload;
                const existingTasksMap = new Map(
                    state.tasks.map(t => [t.id, t])
                );
                
                // Update existing tasks with server data, preserving client fields
                state.tasks = serverTasks.map(serverTask => {
                    const existing = existingTasksMap.get(serverTask.id);
                    return {
                        ...serverTask,
                        analysisStatus: serverTask.is_prioritized
                            ? TaskAnalysisStatus.COMPLETED
                            : existing?.analysisStatus ?? TaskAnalysisStatus.PENDING,
                        pollingAttempts: existing?.pollingAttempts ?? 0,
                        analysisStartedAt: existing?.analysisStartedAt,
                        analysisError: existing?.analysisError,
                    };
                });
                
                // Keep any optimistic/pending tasks not yet on server
                const serverIds = new Set(serverTasks.map(t => t.id));
                const pendingTasks = Array.from(existingTasksMap.values()).filter(
                    t => t.id < 0 || (!serverIds.has(t.id) && !t.is_prioritized)
                );
                
                state.tasks = [...pendingTasks, ...state.tasks];
            })
            .addCase(getPrioritizedTasks.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            })
            
            // -----------------------------------------------------------------
            // ADD TASK (with optimistic update)
            // -----------------------------------------------------------------
            .addCase(addTask.pending, (state, action) => {
                // Create optimistic task with temporary negative ID
                const tempId = Date.now() * -1;
                const payload = action.meta.arg;
                
                const optimisticTask: Task = {
                    id: tempId,
                    user: 0,
                    user_email: '',
                    title: payload.title,
                    description: payload.description ?? '',
                    due_date: payload.due_date ?? null,
                    effort_estimate: payload.effort_estimate ?? 3,
                    is_completed: false,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    priority_score: 0,
                    goal: payload.goal ?? null,
                    goal_weight: null,
                    is_prioritized: false,
                    // Client-side tracking
                    analysisStatus: TaskAnalysisStatus.PENDING,
                    pollingAttempts: 0,
                    analysisStartedAt: new Date().toISOString(),
                };
                
                // Add to beginning of list
                state.tasks.unshift(optimisticTask);
            })
            .addCase(addTask.fulfilled, (state, action: PayloadAction<Task>) => {
                const serverTask = action.payload;
                const payload = action.meta.arg;
                
                // Find and replace the optimistic task
                const idx = state.tasks.findIndex(
                    t => t.id < 0 && t.title === payload.title
                );
                
                if (idx !== -1) {
                    // Replace optimistic with server task, keeping pending status
                    state.tasks[idx] = {
                        ...serverTask,
                        analysisStatus: TaskAnalysisStatus.PENDING,
                        pollingAttempts: 0,
                        analysisStartedAt: new Date().toISOString(),
                    };
                } else {
                    // No optimistic task found, add fresh
                    state.tasks.unshift({
                        ...serverTask,
                        analysisStatus: TaskAnalysisStatus.PENDING,
                        pollingAttempts: 0,
                        analysisStartedAt: new Date().toISOString(),
                    });
                }
            })
            .addCase(addTask.rejected, (state, action) => {
                // Remove the optimistic task
                const payload = action.meta.arg;
                state.tasks = state.tasks.filter(
                    t => !(t.id < 0 && t.title === payload.title)
                );
                state.error = (action.payload as string) || 'Failed to create task.';
            })
            
            // -----------------------------------------------------------------
            // COMPLETE TASK
            // -----------------------------------------------------------------
            .addCase(completeTask.pending, (state, action) => {
                // Optimistic: mark as completed immediately
                const task = state.tasks.find(t => t.id === action.meta.arg);
                if (task) {
                    task.is_completed = true;
                }
            })
            .addCase(completeTask.fulfilled, (state, action: PayloadAction<Task>) => {
                // Remove from active list (completed tasks go to separate view)
                state.tasks = state.tasks.filter(t => t.id !== action.payload.id);
            })
            .addCase(completeTask.rejected, (state, action) => {
                // Rollback optimistic update
                const task = state.tasks.find(t => t.id === action.meta.arg);
                if (task) {
                    task.is_completed = false;
                }
                state.error = (action.payload as string) || 'Failed to complete task.';
            })
            
            // -----------------------------------------------------------------
            // REMOVE TASK
            // -----------------------------------------------------------------
            .addCase(removeTask.pending, (state, action) => {
                // Optimistic: remove immediately
                const taskId = action.meta.arg;
                const task = state.tasks.find(t => t.id === taskId);
                if (task) {
                    // Store for potential rollback (could use a separate field)
                    (state as any)._removedTask = { ...task };
                }
                state.tasks = state.tasks.filter(t => t.id !== taskId);
            })
            .addCase(removeTask.fulfilled, (state) => {
                // Cleanup rollback data
                delete (state as any)._removedTask;
            })
            .addCase(removeTask.rejected, (state, action) => {
                // Rollback: restore the task
                const removed = (state as any)._removedTask;
                if (removed) {
                    state.tasks.unshift(removed);
                    delete (state as any)._removedTask;
                }
                state.error = (action.payload as string) || 'Failed to delete task.';
            })
            
            // -----------------------------------------------------------------
            // RETRY PRIORITIZATION
            // -----------------------------------------------------------------
            .addCase(retryTaskPrioritization.pending, (state, action) => {
                const task = state.tasks.find(t => t.id === action.meta.arg);
                if (task) {
                    task.analysisStatus = TaskAnalysisStatus.PENDING;
                    task.pollingAttempts = 0;
                    task.analysisError = undefined;
                    task.analysisStartedAt = new Date().toISOString();
                }
            })
            .addCase(retryTaskPrioritization.fulfilled, (state, action: PayloadAction<Task>) => {
                const idx = state.tasks.findIndex(t => t.id === action.payload.id);
                if (idx !== -1) {
                    state.tasks[idx] = {
                        ...action.payload,
                        analysisStatus: TaskAnalysisStatus.PENDING,
                        pollingAttempts: 0,
                        analysisStartedAt: new Date().toISOString(),
                    };
                }
            })
            .addCase(retryTaskPrioritization.rejected, (state, action) => {
                const task = state.tasks.find(t => t.id === action.meta.arg);
                if (task) {
                    task.analysisStatus = TaskAnalysisStatus.FAILED;
                    task.analysisError = (action.payload as string) || 'Retry failed';
                }
            });
    },
});


// ---------------------------------------------------------------------------
// SELECTORS
// ---------------------------------------------------------------------------

/**
 * Select all tasks.
 */
export const selectAllTasks = (state: RootState): Task[] => state.tasks.tasks;

/**
 * Select tasks that have completed prioritization.
 */
export const selectPrioritizedTasks = (state: RootState): Task[] =>
    state.tasks.tasks.filter(t => t.is_prioritized);

/**
 * Select tasks that need polling (pending or analyzing).
 */
export const selectTasksNeedingPolling = (state: RootState): Task[] =>
    state.tasks.tasks.filter(needsPolling);

/**
 * Select tasks by analysis status.
 */
export const selectTasksByStatus = (
    state: RootState,
    status: TaskAnalysisStatus
): Task[] =>
    state.tasks.tasks.filter(t => t.analysisStatus === status);

/**
 * Select pending tasks (awaiting analysis).
 */
export const selectPendingTasks = (state: RootState): Task[] =>
    state.tasks.tasks.filter(
        t =>
            t.analysisStatus === TaskAnalysisStatus.PENDING ||
            t.analysisStatus === TaskAnalysisStatus.ANALYZING ||
            (!t.is_prioritized && !t.analysisStatus)
    );

/**
 * Select failed tasks (need retry).
 */
export const selectFailedTasks = (state: RootState): Task[] =>
    state.tasks.tasks.filter(
        t =>
            t.analysisStatus === TaskAnalysisStatus.FAILED ||
            t.analysisStatus === TaskAnalysisStatus.TIMED_OUT
    );

/**
 * Select tasks grouped by quadrant.
 */
export const selectTasksByQuadrant = (state: RootState): Record<Quadrant | 'PENDING', Task[]> => {
    const grouped: Record<Quadrant | 'PENDING', Task[]> = {
        Q1: [],
        Q2: [],
        Q3: [],
        Q4: [],
        PENDING: [],
    };
    
    state.tasks.tasks.forEach(task => {
        if (!task.is_prioritized || !task.quadrant) {
            grouped.PENDING.push(task);
        } else {
            grouped[task.quadrant].push(task);
        }
    });
    
    return grouped;
};

/**
 * Select loading state.
 */
export const selectTasksLoading = (state: RootState): boolean => state.tasks.loading;

/**
 * Select error state.
 */
export const selectTasksError = (state: RootState): string | null => state.tasks.error;

// Legacy selector alias
export const selectTasks = selectAllTasks;


// ---------------------------------------------------------------------------
// EXPORTS
// ---------------------------------------------------------------------------

export const {
    removeTaskLocally,
    updateTaskStatus,
    updateTaskFromServer,
    incrementPollingAttempt,
    markTaskTimedOut,
    markTaskFailed,
    clearError,
    resetAllAnalysisStates,
} = tasksSlice.actions;

export default tasksSlice.reducer;
