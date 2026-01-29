// /src/lib/weights-api.ts
/**
 * Strategic Weights API Functions
 * ================================
 * 
 * API functions for managing user's strategic weights.
 */

import apiClient from '@/lib/apiClient';
import { StrategicWeights, WeightsUpdatePayload } from '@/types/weights';

const WEIGHTS_URL = '/goals/weights/';

/**
 * Fetch the current user's strategic weights.
 * 
 * If the user has no weights configured, the server creates
 * default weights (0.25 each) and returns them.
 */
export async function fetchWeights(): Promise<StrategicWeights> {
    const response = await apiClient.get<StrategicWeights>(WEIGHTS_URL);
    return response.data;
}

/**
 * Update the user's strategic weights.
 * 
 * Supports partial updates - only send the weights you want to change.
 * However, the total sum must still equal 1.0 after the update.
 * 
 * @throws Error if weights don't sum to 1.0 (400 Bad Request)
 */
export async function updateWeights(
    payload: WeightsUpdatePayload
): Promise<StrategicWeights> {
    const response = await apiClient.patch<StrategicWeights>(WEIGHTS_URL, payload);
    return response.data;
}

/**
 * Reset weights to default values (0.25 each).
 */
export async function resetWeights(): Promise<StrategicWeights> {
    const response = await apiClient.patch<StrategicWeights>(WEIGHTS_URL, {
        work_bills: 0.25,
        study: 0.25,
        health: 0.25,
        relationships: 0.25,
    });
    return response.data;
}
