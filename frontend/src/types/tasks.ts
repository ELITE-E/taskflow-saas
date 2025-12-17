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
    priority_score:number; //score calculated by comput.py
    goal:number | null;
    goal_weight:number|null;
    is_prioritized: boolean;    // The boolean flag we added to the model
    async_status_id?: string;   // The Celery Task ID (optional)
    quadrant?: 'Q1' | 'Q2' | 'Q3' | 'Q4';// Optional: If you've implemented the Quadrant logic
}

// Interface for data sent when creating/updating
export interface TaskPayload {
    title: string;
    description?: string;
    due_date?: string | null;
    effort_estimate?: number;
    is_completed?: boolean;
    goal?:number |null ;
}