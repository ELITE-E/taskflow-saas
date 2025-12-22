// /src/redux/slices/tasksSlice.ts

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Task, TaskPayload } from '@/types/tasks';
import * as tasksApi from '@/lib/tasks-api';

interface TasksState {
    tasks: Task[];
    loading: boolean;
    error: string | null;
}

const initialState: TasksState = {
    tasks: [],
    loading: false,
    error: null,
};

// --- ASYNCHRONOUS THUNKS ---

export const getPrioritizedTasks = createAsyncThunk<Task[], void>(
    'tasks/getPrioritizedTasks',
    async (_, { rejectWithValue }) => {
        try {
            return await tasksApi.fetchPrioritizedTasks();
        } catch (error: any) {
            return rejectWithValue(error.response?.data?.detail || 'Failed to fetch tasks.');
        }
    }
);

export const addTask = createAsyncThunk<Task, TaskPayload>(
    'tasks/addTask',
    async (payload, { rejectWithValue }) => {
        try {
            return await tasksApi.createTask(payload);
        } catch (error: any) {
            return rejectWithValue(error.response?.data || 'Failed to create task.');
        }
    }
);

export const completeTask = createAsyncThunk<Task, number>(
    'tasks/completeTask',
    async (taskId, { rejectWithValue }) => {
        try {
            const updatedTask = await tasksApi.updateTask(taskId, { is_completed: true });
            return updatedTask;
        } catch (error: any) {
            return rejectWithValue(error.response?.data || 'Failed to complete task.');
        }
    }
);

export const removeTask = createAsyncThunk<number, number>(
    'tasks/removeTask',
    async (taskId, { rejectWithValue }) => {
        try {
            await tasksApi.deleteTask(taskId);
            return taskId;
        } catch (error: any) {
            return rejectWithValue(error.response?.data?.detail || 'Failed to delete task.');
        }
    }
);

// --- SELECTORS (derived, not stored) ---
export const selectTasks = (state: any) => state.tasks.tasks;
export const selectPrioritizedTasks = (state: any) =>
    (state.tasks.tasks || []).filter((t: Task) => Boolean(t.is_prioritized));

// --- SLICE DEFINITION ---
const tasksSlice = createSlice({
    name: 'tasks',
    initialState,
    reducers: {
        removeTaskLocally: (state, action: PayloadAction<number>) => {
            state.tasks = state.tasks.filter(task => task.id !== action.payload);
        }
    },
    extraReducers: (builder) => {
        builder
            // GET TASKS
            .addCase(getPrioritizedTasks.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(getPrioritizedTasks.fulfilled, (state, action: PayloadAction<Task[]>) => {
                state.loading = false;
                state.tasks = action.payload;
            })
            .addCase(getPrioritizedTasks.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
                state.tasks = [];
            })

            // ADD TASK: optimistic insert on pending, reconcile on fulfilled/rejected
            .addCase(addTask.pending, (state, action) => {
                // optimistic task with temporary negative id
                const tempId = Date.now() * -1;
                const arg = action.meta.arg as TaskPayload;
                const tempTask: Task = {
                    id: tempId,
                    user: 0,
                    user_email: '',
                    title: arg.title,
                    description: arg.description ?? '',
                    due_date: arg.due_date ?? null,
                    effort_estimate: arg.effort_estimate ?? 3,
                    is_completed: false,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    priority_score: 0,
                    goal: null,
                    goal_weight: null,
                    is_prioritized: false,
                    async_status_id: undefined,
                } as Task;
                state.tasks.unshift(tempTask);
            })
            .addCase(addTask.fulfilled, (state, action: PayloadAction<Task>) => {
                // Replace optimistic task if present (match by negative id & same title), else prepend
                const returned = action.payload;
                const idx = state.tasks.findIndex(t => t.id < 0 && t.title === returned.title);
                if (idx !== -1) {
                    state.tasks[idx] = returned;
                } else {
                    state.tasks.unshift(returned);
                }
            })
            .addCase(addTask.rejected, (state, action) => {
                // Remove any optimistic entry that matches the rejected arg
                const arg = action.meta.arg as TaskPayload;
                state.tasks = state.tasks.filter(t => !(t.id < 0 && t.title === arg.title));
                state.error = action.payload as string || 'Failed to create task.';
            })

            // COMPLETE TASK
            .addCase(completeTask.fulfilled, (state, action: PayloadAction<Task>) => {
                state.tasks = state.tasks.filter(t => t.id !== action.payload.id);
            })

            // REMOVE TASK
            .addCase(removeTask.fulfilled, (state, action: PayloadAction<number>) => {
                state.tasks = state.tasks.filter(t => t.id !== action.payload);
            });
    },
});

export const { removeTaskLocally } = tasksSlice.actions;
export default tasksSlice.reducer;