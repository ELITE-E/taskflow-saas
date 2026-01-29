// /src/types/weights.ts
/**
 * Strategic Weights Type Definitions
 * ===================================
 * 
 * Types for the user's strategic value configuration.
 * 
 * The Four Domains:
 * -----------------
 * 1. Work/Bills: Career, finances, professional obligations
 * 2. Study: Education, learning, skill development
 * 3. Health: Physical fitness, mental well-being, medical
 * 4. Relationships: Family, friends, social connections
 * 
 * Normalization Constraint:
 * -------------------------
 * All weights must sum to exactly 1.0 (100%).
 * This ensures task importance scores are properly normalized.
 */

// ---------------------------------------------------------------------------
// CORE INTERFACES
// ---------------------------------------------------------------------------

/**
 * User's strategic weights configuration.
 */
export interface StrategicWeights {
    /** Unique identifier */
    id: number;
    
    /** Weight for work and financial tasks (0.0 - 1.0) */
    work_bills: number;
    
    /** Weight for education and learning tasks (0.0 - 1.0) */
    study: number;
    
    /** Weight for health and wellness tasks (0.0 - 1.0) */
    health: number;
    
    /** Weight for relationship tasks (0.0 - 1.0) */
    relationships: number;
    
    /** Computed: sum of all weights (should be 1.0) */
    total_sum: number;
    
    /** Computed: whether weights are valid (sum ≈ 1.0) */
    is_valid_sum: boolean;
}

/**
 * Payload for updating weights (all fields optional for partial updates).
 */
export interface WeightsUpdatePayload {
    work_bills?: number;
    study?: number;
    health?: number;
    relationships?: number;
}

/**
 * Domain/category identifiers.
 */
export type WeightDomain = 'work_bills' | 'study' | 'health' | 'relationships';

/**
 * All weight domains as array (useful for iteration).
 */
export const WEIGHT_DOMAINS: WeightDomain[] = [
    'work_bills',
    'study',
    'health',
    'relationships',
];


// ---------------------------------------------------------------------------
// DOMAIN METADATA
// ---------------------------------------------------------------------------

/**
 * UI metadata for each domain.
 */
export interface DomainInfo {
    id: WeightDomain;
    label: string;
    shortLabel: string;
    description: string;
    icon: string;
    color: string;
    examples: string[];
}

/**
 * Domain configuration for UI display.
 */
export const DOMAIN_CONFIG: Record<WeightDomain, DomainInfo> = {
    work_bills: {
        id: 'work_bills',
        label: 'Work & Bills',
        shortLabel: 'Work',
        description: 'Career advancement, financial obligations, professional growth',
        icon: '💼',
        color: '#3b82f6', // Blue
        examples: ['Pay invoices', 'Prepare presentation', 'Client meeting'],
    },
    study: {
        id: 'study',
        label: 'Study & Learning',
        shortLabel: 'Study',
        description: 'Education, skill development, courses, reading',
        icon: '📚',
        color: '#8b5cf6', // Purple
        examples: ['Complete online course', 'Read technical book', 'Practice coding'],
    },
    health: {
        id: 'health',
        label: 'Health & Wellness',
        shortLabel: 'Health',
        description: 'Physical fitness, mental health, medical appointments',
        icon: '🏃',
        color: '#10b981', // Green
        examples: ['Go to gym', 'Meditation session', 'Doctor appointment'],
    },
    relationships: {
        id: 'relationships',
        label: 'Relationships',
        shortLabel: 'Social',
        description: 'Family, friends, social connections, community',
        icon: '❤️',
        color: '#f43f5e', // Pink/Red
        examples: ['Call parents', 'Date night', 'Team lunch'],
    },
};


// ---------------------------------------------------------------------------
// UTILITY FUNCTIONS
// ---------------------------------------------------------------------------

/**
 * Calculate the sum of all weights.
 */
export function calculateWeightSum(weights: Partial<StrategicWeights>): number {
    const values = [
        weights.work_bills ?? 0,
        weights.study ?? 0,
        weights.health ?? 0,
        weights.relationships ?? 0,
    ];
    
    const sum = values.reduce((acc, val) => acc + val, 0);
    // Round to avoid floating-point display issues
    return Math.round(sum * 10000) / 10000;
}

/**
 * Check if weights are valid (sum to 1.0 within epsilon).
 */
export function isValidWeightSum(sum: number): boolean {
    return sum >= 0.999 && sum <= 1.001;
}

/**
 * Get display percentage from decimal weight.
 * Handles floating-point precision issues.
 */
export function weightToPercent(weight: number): number {
    return Math.round(weight * 100);
}

/**
 * Convert percentage to decimal weight.
 */
export function percentToWeight(percent: number): number {
    return Math.round(percent) / 100;
}

/**
 * Format weight as percentage string.
 */
export function formatWeightPercent(weight: number): string {
    return `${weightToPercent(weight)}%`;
}

/**
 * Get remaining budget (difference from 1.0).
 */
export function getRemainingBudget(currentSum: number): number {
    const remaining = 1.0 - currentSum;
    return Math.round(remaining * 10000) / 10000;
}

/**
 * Default weights (equal distribution).
 */
export const DEFAULT_WEIGHTS: Omit<StrategicWeights, 'id' | 'total_sum' | 'is_valid_sum'> = {
    work_bills: 0.25,
    study: 0.25,
    health: 0.25,
    relationships: 0.25,
};
