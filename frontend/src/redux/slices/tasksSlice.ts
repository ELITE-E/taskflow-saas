// /src/redux/slices/tasksSlice.ts

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Task, TaskPayload } from '@/types/tasks';
import * as tasksApi from '@/lib/tasks-api';

interface TasksState {
    tasks: Task[];
    prioritizedItems:Task[];
    loading: boolean;
    error: string | null;
}

const initialState: TasksState = {
    tasks: [],
    prioritizedItems:[],
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
export const selectPrioritizedTasks = (state: any) => state.tasks.tasks;
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
            // Update the task to set is_completed=true
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
            return taskId; // Return ID to remove from state
        } catch (error: any) {
            return rejectWithValue(error.response?.data?.detail || 'Failed to delete task.');
        }
    }
);


// --- SLICE DEFINITION ---
const tasksSlice = createSlice({
    name: 'tasks',
    initialState,
    reducers: {
        // Reducer to handle task deletion in UI without relying on API response
        removeTaskLocally: (state, action: PayloadAction<number>) => {
            state.tasks = state.tasks.filter(task => task.id !== action.payload);
        }
    },
    extraReducers: (builder) => {
        builder
            // --- GET TASKS ---
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
                state.tasks=[];
            })
            // --- ADD TASK ---
            .addCase(addTask.fulfilled, (state, action: PayloadAction<Task>) => {
                state.tasks.unshift(action.payload); // Add new task to the start
            })
            // --- COMPLETE TASK ---
            .addCase(completeTask.fulfilled, (state, action: PayloadAction<Task>) => {
                // Since the backend filters out completed tasks, we simply remove it from the list.
                state.tasks = state.tasks.filter(t => t.id !== action.payload.id);
            })
            // --- REMOVE TASK ---
            .addCase(removeTask.fulfilled, (state, action: PayloadAction<number>) => {
                // Remove task by ID
                state.tasks = state.tasks.filter(t => t.id !== action.payload);
            })
            // Handle pending/rejected for other thunks if necessary
    },
});

export const { removeTaskLocally } = tasksSlice.actions;
export default tasksSlice.reducer;