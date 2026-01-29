import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authReducer';
import goalsReducer from './slices/goalsSlice';
import tasksReducer from './slices/tasksSlice';
import weightsReducer from './slices/weightsSlice';

/**
 * Redux Store Configuration
 * =========================
 * 
 * Central state management for the TaskFlow application.
 * 
 * Slices:
 * - auth: User authentication state
 * - goals: User's strategic goals
 * - tasks: Task list and prioritization state
 * - weights: Strategic weights for AI prioritization
 */
export const store = configureStore({
    reducer: {
        auth: authReducer,
        goals: goalsReducer,
        tasks: tasksReducer,
        weights: weightsReducer,
    },
});

// Type exports for TypeScript support
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;