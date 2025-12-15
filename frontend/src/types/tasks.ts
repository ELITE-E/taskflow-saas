// /src/types/tasks.ts

export interface Task {
    id: number;
    user: number;
    user_email: string; 
    title: string;
    description: string;
    due_date: string | null; // Date can be null
    effort_estimate: number; // 1-5 effort
    is_completed: boolean;
    created_at: string;
    updated_at: string;
}

// Interface for data sent when creating/updating
export interface TaskPayload {
    title: string;
    description?: string;
    due_date?: string | null;
    effort_estimate?: number;
    is_completed?: boolean;
}