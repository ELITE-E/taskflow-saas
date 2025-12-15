// /src/services/goals-api.ts

import apiClient from '@/lib/apiClient'; // Our secured Axios instance
import { Goal, GoalPayload } from '@/types/goals';

const GOALS_BASE_URL = '/goals/'; // Matches our backend config: /api/v1/goals/

/**
 * Fetches all non-archived goals for the authenticated user.
 */
export const fetchGoals = async (): Promise<Goal[]> => {
    const response = await apiClient.get(GOALS_BASE_URL);
    return response.data;
};

/**
 * Creates a new goal.
 */
export const createGoal = async (payload: GoalPayload): Promise<Goal> => {
    const response = await apiClient.post(GOALS_BASE_URL, payload);
    return response.data;
};

/**
 * Fetches a specific goal by ID.
 */
export const fetchGoalDetail = async (goalId: number): Promise<Goal> => {
    const response = await apiClient.get(`${GOALS_BASE_URL}${goalId}/`);
    return response.data;
};

/**
 * Updates an existing goal (uses PATCH for partial updates).
 */
export const updateGoal = async (goalId: number, payload: Partial<GoalPayload>): Promise<Goal> => {
    // Note: We use PATCH to only send the fields that have changed
    const response = await apiClient.patch(`${GOALS_BASE_URL}${goalId}/`, payload);
    return response.data;
};

/**
 * Archives (Soft-Deletes) a goal.
 */
export const archiveGoal = async (goalId: number): Promise<void> => {
    // We update the 'is_archived' field to true instead of a hard DELETE
    await apiClient.patch(`${GOALS_BASE_URL}${goalId}/`, { is_archived: true });
};

/**
 * Permanently deletes a goal (use sparingly).
 */
export const deleteGoal = async (goalId: number): Promise<void> => {
    await apiClient.delete(`${GOALS_BASE_URL}${goalId}/`);
};