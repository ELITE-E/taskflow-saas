// /src/types/goals.ts

export interface Goal {
    id: number;
    user: number; // ID of the user who owns the goal
    user_email: string; // Read-only email of the owner
    title: string;
    description: string;
    weight: number; // 1-10 importance
    is_archived: boolean;
    created_at: string; // ISO format datetime string
    updated_at: string;
}

// Interface for data sent to the API when creating/updating
export interface GoalPayload {
    title: string;
    description: string;
    weight: number;
    is_archived?: boolean; // Optional for updates
}