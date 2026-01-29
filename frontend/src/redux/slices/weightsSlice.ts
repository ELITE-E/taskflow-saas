// /src/redux/slices/weightsSlice.ts
/**
 * Strategic Weights Redux Slice
 * ==============================
 * 
 * Manages the user's strategic weights state.
 * 
 * Features:
 * - Fetch weights from server
 * - Local preview of changes before saving
 * - Save with validation
 * - Trigger task re-prioritization on save
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import {
    StrategicWeights,
    WeightsUpdatePayload,
    WeightDomain,
    calculateWeightSum,
    isValidWeightSum,
    DEFAULT_WEIGHTS,
} from '@/types/weights';
import * as weightsApi from '@/lib/weights-api';
import { RootState } from '../store';

// ---------------------------------------------------------------------------
// STATE INTERFACE
// ---------------------------------------------------------------------------

interface WeightsState {
    /** Server-confirmed weights */
    weights: StrategicWeights | null;
    
    /** Local draft weights (for preview before saving) */
    draftWeights: Partial<StrategicWeights>;
    
    /** Whether draft differs from saved weights */
    hasUnsavedChanges: boolean;
    
    /** Loading state for API calls */
    loading: boolean;
    
    /** Saving state for update calls */
    saving: boolean;
    
    /** Error message if any */
    error: string | null;
    
    /** Whether weights have been fetched */
    initialized: boolean;
    
    /** Whether a re-prioritization is needed after save */
    needsReprioritization: boolean;
}

const initialState: WeightsState = {
    weights: null,
    draftWeights: {},
    hasUnsavedChanges: false,
    loading: false,
    saving: false,
    error: null,
    initialized: false,
    needsReprioritization: false,
};


// ---------------------------------------------------------------------------
// ASYNC THUNKS
// ---------------------------------------------------------------------------

/**
 * Fetch the user's strategic weights from the server.
 */
export const fetchWeights = createAsyncThunk<StrategicWeights, void>(
    'weights/fetchWeights',
    async (_, { rejectWithValue }) => {
        try {
            return await weightsApi.fetchWeights();
        } catch (error: any) {
            return rejectWithValue(
                error.response?.data?.detail || 'Failed to fetch weights.'
            );
        }
    }
);

/**
 * Save updated weights to the server.
 */
export const saveWeights = createAsyncThunk<StrategicWeights, WeightsUpdatePayload>(
    'weights/saveWeights',
    async (payload, { rejectWithValue }) => {
        try {
            return await weightsApi.updateWeights(payload);
        } catch (error: any) {
            // Extract validation error message
            const errorData = error.response?.data;
            if (errorData?.non_field_errors) {
                return rejectWithValue(errorData.non_field_errors[0]);
            }
            return rejectWithValue(
                errorData?.detail || 'Failed to save weights.'
            );
        }
    }
);

/**
 * Reset weights to default values.
 */
export const resetWeights = createAsyncThunk<StrategicWeights, void>(
    'weights/resetWeights',
    async (_, { rejectWithValue }) => {
        try {
            return await weightsApi.resetWeights();
        } catch (error: any) {
            return rejectWithValue(
                error.response?.data?.detail || 'Failed to reset weights.'
            );
        }
    }
);


// ---------------------------------------------------------------------------
// SLICE DEFINITION
// ---------------------------------------------------------------------------

const weightsSlice = createSlice({
    name: 'weights',
    initialState,
    
    reducers: {
        /**
         * Update a single weight in the draft state.
         * This is used for live preview as the user adjusts sliders.
         */
        setDraftWeight: (
            state,
            action: PayloadAction<{ domain: WeightDomain; value: number }>
        ) => {
            const { domain, value } = action.payload;
            
            // Round to avoid floating-point issues
            const roundedValue = Math.round(value * 100) / 100;
            
            // Update draft
            state.draftWeights = {
                ...state.draftWeights,
                [domain]: roundedValue,
            };
            
            // Mark as changed if different from saved
            state.hasUnsavedChanges = true;
        },
        
        /**
         * Set all draft weights at once (for normalization).
         */
        setAllDraftWeights: (
            state,
            action: PayloadAction<Partial<StrategicWeights>>
        ) => {
            state.draftWeights = {
                work_bills: action.payload.work_bills,
                study: action.payload.study,
                health: action.payload.health,
                relationships: action.payload.relationships,
            };
            state.hasUnsavedChanges = true;
        },
        
        /**
         * Discard draft changes and revert to saved weights.
         */
        discardDraftChanges: (state) => {
            if (state.weights) {
                state.draftWeights = {
                    work_bills: state.weights.work_bills,
                    study: state.weights.study,
                    health: state.weights.health,
                    relationships: state.weights.relationships,
                };
            }
            state.hasUnsavedChanges = false;
            state.error = null;
        },
        
        /**
         * Clear any error state.
         */
        clearWeightsError: (state) => {
            state.error = null;
        },
        
        /**
         * Acknowledge the re-prioritization notification.
         */
        acknowledgeReprioritization: (state) => {
            state.needsReprioritization = false;
        },
    },
    
    extraReducers: (builder) => {
        builder
            // -----------------------------------------------------------------
            // FETCH WEIGHTS
            // -----------------------------------------------------------------
            .addCase(fetchWeights.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchWeights.fulfilled, (state, action) => {
                state.loading = false;
                state.weights = action.payload;
                state.initialized = true;
                
                // Initialize draft with fetched values
                state.draftWeights = {
                    work_bills: action.payload.work_bills,
                    study: action.payload.study,
                    health: action.payload.health,
                    relationships: action.payload.relationships,
                };
                state.hasUnsavedChanges = false;
            })
            .addCase(fetchWeights.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            })
            
            // -----------------------------------------------------------------
            // SAVE WEIGHTS
            // -----------------------------------------------------------------
            .addCase(saveWeights.pending, (state) => {
                state.saving = true;
                state.error = null;
            })
            .addCase(saveWeights.fulfilled, (state, action) => {
                state.saving = false;
                state.weights = action.payload;
                state.hasUnsavedChanges = false;
                state.needsReprioritization = true; // Signal that tasks need refresh
                
                // Sync draft with saved values
                state.draftWeights = {
                    work_bills: action.payload.work_bills,
                    study: action.payload.study,
                    health: action.payload.health,
                    relationships: action.payload.relationships,
                };
            })
            .addCase(saveWeights.rejected, (state, action) => {
                state.saving = false;
                state.error = action.payload as string;
            })
            
            // -----------------------------------------------------------------
            // RESET WEIGHTS
            // -----------------------------------------------------------------
            .addCase(resetWeights.pending, (state) => {
                state.saving = true;
                state.error = null;
            })
            .addCase(resetWeights.fulfilled, (state, action) => {
                state.saving = false;
                state.weights = action.payload;
                state.draftWeights = {
                    work_bills: action.payload.work_bills,
                    study: action.payload.study,
                    health: action.payload.health,
                    relationships: action.payload.relationships,
                };
                state.hasUnsavedChanges = false;
                state.needsReprioritization = true;
            })
            .addCase(resetWeights.rejected, (state, action) => {
                state.saving = false;
                state.error = action.payload as string;
            });
    },
});


// ---------------------------------------------------------------------------
// SELECTORS
// ---------------------------------------------------------------------------

/**
 * Select the saved weights.
 */
export const selectWeights = (state: RootState): StrategicWeights | null =>
    state.weights.weights;

/**
 * Select the draft weights (with fallback to saved or defaults).
 */
export const selectDraftWeights = (state: RootState): Partial<StrategicWeights> => {
    const draft = state.weights.draftWeights;
    const saved = state.weights.weights;
    
    return {
        work_bills: draft.work_bills ?? saved?.work_bills ?? DEFAULT_WEIGHTS.work_bills,
        study: draft.study ?? saved?.study ?? DEFAULT_WEIGHTS.study,
        health: draft.health ?? saved?.health ?? DEFAULT_WEIGHTS.health,
        relationships: draft.relationships ?? saved?.relationships ?? DEFAULT_WEIGHTS.relationships,
    };
};

/**
 * Select the current draft sum.
 */
export const selectDraftSum = (state: RootState): number => {
    const draft = selectDraftWeights(state);
    return calculateWeightSum(draft);
};

/**
 * Select whether the draft sum is valid.
 */
export const selectIsDraftValid = (state: RootState): boolean => {
    const sum = selectDraftSum(state);
    return isValidWeightSum(sum);
};

/**
 * Select whether there are unsaved changes.
 */
export const selectHasUnsavedChanges = (state: RootState): boolean =>
    state.weights.hasUnsavedChanges;

/**
 * Select loading state.
 */
export const selectWeightsLoading = (state: RootState): boolean =>
    state.weights.loading;

/**
 * Select saving state.
 */
export const selectWeightsSaving = (state: RootState): boolean =>
    state.weights.saving;

/**
 * Select error state.
 */
export const selectWeightsError = (state: RootState): string | null =>
    state.weights.error;

/**
 * Select whether re-prioritization is needed.
 */
export const selectNeedsReprioritization = (state: RootState): boolean =>
    state.weights.needsReprioritization;


// ---------------------------------------------------------------------------
// EXPORTS
// ---------------------------------------------------------------------------

export const {
    setDraftWeight,
    setAllDraftWeights,
    discardDraftChanges,
    clearWeightsError,
    acknowledgeReprioritization,
} = weightsSlice.actions;

export default weightsSlice.reducer;
