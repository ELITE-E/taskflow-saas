// /src/redux/slices/goalsSlice.ts

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Goal, GoalPayload } from '@/types/goals';
import * as goalsApi from '@/lib/goals-api';

// 1. Define the initial state structure
interface GoalsState {
    goals: Goal[];
    loading: boolean;
    error: string | null;
}

const initialState: GoalsState = {
    goals: [],
    loading: false,
    error: null,
};

// 2. Define Asynchronous Thunks

// Thunk to fetch all goals
export const getGoals = createAsyncThunk<Goal[], void>(
    'goals/getGoals',
    async (_, { rejectWithValue }) => {
        try {
            return await goalsApi.fetchGoals();
        } catch (error: any) {
            return rejectWithValue(error.response?.data?.detail || 'Failed to fetch goals.');
        }
    }
);

// Thunk to create a new goal
export const addGoal = createAsyncThunk<Goal, GoalPayload>(
    'goals/addGoal',
    async (payload, { rejectWithValue }) => {
        try {
            return await goalsApi.createGoal(payload);
        } catch (error: any) {
            return rejectWithValue(error.response?.data || 'Failed to create goal.');
        }
    }
);

// Thunk to update a goal
export const modifyGoal = createAsyncThunk<Goal, { id: number; payload: Partial<GoalPayload> }>(
    'goals/modifyGoal',
    async ({ id, payload }, { rejectWithValue }) => {
        try {
            return await goalsApi.updateGoal(id, payload);
        } catch (error: any) {
            return rejectWithValue(error.response?.data || 'Failed to update goal.');
        }
    }
);

// Thunk to archive a goal
export const archiveGoal = createAsyncThunk<number, number>(
    'goals/archiveGoal',
    async (goalId, { rejectWithValue }) => {
        try {
            await goalsApi.archiveGoal(goalId);
            return goalId; // Return ID to remove it from the list state
        } catch (error: any) {
            return rejectWithValue(error.response?.data?.detail || 'Failed to archive goal.');
        }
    }
);

// 3. Create the Goals Slice
const goalsSlice = createSlice({
    name: 'goals',
    initialState,
    reducers: {
        clearGoalsError: (state) => {
            state.error = null;
        }
    },
    extraReducers: (builder) => {
        builder
            // --- GET GOALS ---
            .addCase(getGoals.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(getGoals.fulfilled, (state, action: PayloadAction<Goal[]>) => {
                state.loading = false;
                state.goals = action.payload;
            })
            .addCase(getGoals.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
                state.goals = [];
            })
            // --- ADD GOAL ---
            .addCase(addGoal.fulfilled, (state, action: PayloadAction<Goal>) => {
                // Add the new goal to the front of the list
                state.goals.unshift(action.payload); 
            })
            // --- MODIFY GOAL ---
            .addCase(modifyGoal.fulfilled, (state, action: PayloadAction<Goal>) => {
                const index = state.goals.findIndex(g => g.id === action.payload.id);
                if (index !== -1) {
                    // Replace the old goal object with the updated one
                    state.goals[index] = action.payload; 
                }
            })
            // --- ARCHIVE GOAL ---
            .addCase(archiveGoal.fulfilled, (state, action: PayloadAction<number>) => {
                // Remove the archived goal from the active list
                state.goals = state.goals.filter(g => g.id !== action.payload); 
            })
            // Handle pending/rejected for add/modify/archive if needed (omitted for brevity)
    },
});

export const { clearGoalsError } = goalsSlice.actions;
export default goalsSlice.reducer;