import apiClient from '@/lib/apiClient';
import { Task, TaskPayload } from '@/types/tasks';

const TASKS_BASE_URL = '/tasks/';
const TASK_PRIORITIZE_URL = '/tasks/prioritized-list/'; // fixed to match backend

export const fetchPrioritizedTasks = async (): Promise<Task[]> => {
  const response = await apiClient.get<Task[]>(TASK_PRIORITIZE_URL);
  return response.data;
};

export const createTask = async (payload: TaskPayload): Promise<Task> => {
  const response = await apiClient.post<Task>(TASKS_BASE_URL, payload);
  return response.data;
};

export const updateTask = async (taskId: number, payload: Partial<TaskPayload>): Promise<Task> => {
  const response = await apiClient.patch<Task>(`${TASKS_BASE_URL}${taskId}/`, payload);
  return response.data;
};

export const deleteTask = async (taskId: number): Promise<void> => {
  await apiClient.delete(`${TASKS_BASE_URL}${taskId}/`);
};