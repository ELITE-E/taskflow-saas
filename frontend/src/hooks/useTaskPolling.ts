// src/hooks/useTaskPolling.ts

import { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '@/redux/store';
import { getPrioritizedTasks } from '@/redux/slices/tasksSlice';
import apiClient from '@/lib/apiClient';
import { Task } from '@/types/tasks';

export const useTaskPolling = (pollingInterval = 3000) => {
    const dispatch = useDispatch<AppDispatch>();
    const { tasks } = useSelector((state: RootState) => state.tasks);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    // Identify tasks that were created but haven't been processed by AI yet
    const pendingTaskIds = tasks
        .filter(task => !task.is_prioritized)
        .map(task => task.id);

    useEffect(() => {
        // If there are pending tasks, start polling
        if (pendingTaskIds.length > 0) {
            if (!intervalRef.current) {
                intervalRef.current = setInterval(async () => {
                    try {
                        // Check the status of the first pending task
                        // (Simplified: if one is done, we refresh the whole prioritized list)
                        const results = await Promise.all(
                            pendingTaskIds.map(id => apiClient.get<Task>(`/tasks/${id}/`))
                        );

                        const anyFinished = results.some(res => res.data.is_prioritized);

                        if (anyFinished) {
                            // Trigger Redux to fetch the new prioritized order
                            dispatch(getPrioritizedTasks());
                            
                            // Clear interval if all are finished
                            if (results.every(res => res.data.is_prioritized)) {
                                if (intervalRef.current) clearInterval(intervalRef.current);
                                intervalRef.current = null;
                            }
                        }
                    } catch (error) {
                        console.error("Polling error:", error);
                    }
                }, pollingInterval);
            }
        } else {
            // Cleanup if no pending tasks exist
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        }

        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [pendingTaskIds, dispatch, pollingInterval]);
};