import apiClient from '@/lib/apiClient'; 
import { Task, TaskPayload } from '@/types/tasks';

const TASKS_BASE_URL = '/tasks/'; // Matches our backend config: /api/v1/tasks/
const TASK_PRIORITIZE_URL='/tasks/prioritize-list/';

/** Fetches the prioritized tasks list sorted by the tsk score */

export const fetchPrioritizedTasks=async():Promise<Task[]>=>{
    const response= await apiClient.get<Task[]>(TASK_PRIORITIZE_URL);
    return response.data}

/**
 * Creates a new task.
 */
export const createTask = async (payload: TaskPayload): Promise<Task> => {
    const response = await apiClient.post(TASKS_BASE_URL, payload);
    return response.data;
};

/**
 * Updates an existing task (e.g., setting is_completed to true).
 */
export const updateTask = async (taskId: number, payload: Partial<TaskPayload>): Promise<Task> => {
    // We use PATCH for partial updates
    const response = await apiClient.patch(`${TASKS_BASE_URL}${taskId}/`, payload);
    return response.data;
};

/**
 * Permanently deletes a task.
 */
export const deleteTask = async (taskId: number): Promise<void> => {
    await apiClient.delete(`${TASKS_BASE_URL}${taskId}/`);
};