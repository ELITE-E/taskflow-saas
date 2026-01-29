// src/components/tasks/PrioritizationMatrix.tsx
/**
 * Prioritization Matrix Component
 * ================================
 * 
 * Visualizes tasks in the Eisenhower Matrix (Q1-Q4) with:
 * - Real-time status indicators for analyzing tasks
 * - Pending tasks area for tasks awaiting AI processing
 * - Error handling with retry functionality
 * - Optimistic updates for snappy UX
 */

import React, { useCallback, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
    selectPrioritizedTasks,
    selectPendingTasks,
    selectFailedTasks,
    retryTaskPrioritization,
} from '../../redux/slices/tasksSlice';
import { useTaskPolling } from '../../hooks/useTaskPolling';
import {
    Task,
    TaskAnalysisStatus,
    Quadrant,
    QUADRANT_CONFIG,
    GroupedTasks,
    getStatusLabel,
} from '@/types/tasks';
import { AppDispatch } from '@/redux/store';


// ---------------------------------------------------------------------------
// MAIN COMPONENT
// ---------------------------------------------------------------------------

/**
 * The main Eisenhower Matrix visualization component.
 */
const PrioritizationMatrix: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>();
    
    // Select tasks by status
    const prioritizedTasks = useSelector(selectPrioritizedTasks);
    const pendingTasks = useSelector(selectPendingTasks);
    const failedTasks = useSelector(selectFailedTasks);
    
    // Initialize smart polling
    const { isPolling, pollingCount, retryTask } = useTaskPolling({
        enabled: true,
        onTaskComplete: (task) => {
            console.log(`Task "${task.title}" prioritization complete:`, task.quadrant);
        },
        onTaskError: (task, error) => {
            console.warn(`Task "${task.title}" polling error:`, error);
        },
    });
    
    // Group prioritized tasks by quadrant
    const grouped: GroupedTasks = useMemo(() => {
        return prioritizedTasks.reduce(
            (acc, task) => {
                const quadrant = task.quadrant as Quadrant;
                if (quadrant && quadrant in acc) {
                    acc[quadrant].push(task);
                }
                return acc;
            },
            { Q1: [], Q2: [], Q3: [], Q4: [] } as GroupedTasks
        );
    }, [prioritizedTasks]);
    
    // Handle retry button click
    const handleRetry = useCallback((taskId: number) => {
        dispatch(retryTaskPrioritization(taskId));
        retryTask(taskId);
    }, [dispatch, retryTask]);
    
    return (
        <div style={containerStyle}>
            {/* Header with polling status */}
            <header style={headerStyle}>
                <h2 style={{ margin: 0 }}>Strategic Task Matrix</h2>
                {isPolling && (
                    <PollingIndicator count={pollingCount} />
                )}
            </header>
            
            {/* Pending Tasks Section */}
            {(pendingTasks.length > 0 || failedTasks.length > 0) && (
                <PendingTasksSection
                    pendingTasks={pendingTasks}
                    failedTasks={failedTasks}
                    onRetry={handleRetry}
                />
            )}
            
            {/* Main Matrix Grid */}
            <div style={matrixGridStyle}>
                {(['Q1', 'Q2', 'Q3', 'Q4'] as Quadrant[]).map(quadrant => (
                    <QuadrantSection
                        key={quadrant}
                        quadrant={quadrant}
                        tasks={grouped[quadrant]}
                    />
                ))}
            </div>
        </div>
    );
};


// ---------------------------------------------------------------------------
// SUB-COMPONENTS
// ---------------------------------------------------------------------------

/**
 * Polling status indicator.
 */
const PollingIndicator: React.FC<{ count: number }> = ({ count }) => (
    <div style={pollingIndicatorStyle}>
        <span style={spinnerStyle}>◌</span>
        <span>Analyzing {count} task{count !== 1 ? 's' : ''}...</span>
    </div>
);

/**
 * Section displaying pending and failed tasks.
 */
interface PendingTasksSectionProps {
    pendingTasks: Task[];
    failedTasks: Task[];
    onRetry: (taskId: number) => void;
}

const PendingTasksSection: React.FC<PendingTasksSectionProps> = ({
    pendingTasks,
    failedTasks,
    onRetry,
}) => (
    <div style={pendingSectionStyle}>
        <h3 style={pendingHeaderStyle}>
            <span style={pendingIconStyle}>⏳</span>
            Awaiting Prioritization
        </h3>
        
        <div style={pendingListStyle}>
            {/* Pending/Analyzing Tasks */}
            {pendingTasks.map(task => (
                <TaskCard
                    key={task.id}
                    task={task}
                    variant="pending"
                />
            ))}
            
            {/* Failed/Timed Out Tasks */}
            {failedTasks.map(task => (
                <TaskCard
                    key={task.id}
                    task={task}
                    variant="failed"
                    onRetry={() => onRetry(task.id)}
                />
            ))}
        </div>
    </div>
);

/**
 * Individual task card with status indicator.
 */
interface TaskCardProps {
    task: Task;
    variant: 'pending' | 'failed' | 'normal';
    onRetry?: () => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, variant, onRetry }) => {
    const status = task.analysisStatus;
    const isAnalyzing = status === TaskAnalysisStatus.ANALYZING;
    const isFailed = status === TaskAnalysisStatus.FAILED || status === TaskAnalysisStatus.TIMED_OUT;
    
    // Determine card style based on variant
    const cardStyle: React.CSSProperties = {
        ...baseCardStyle,
        ...(variant === 'pending' && pendingCardStyle),
        ...(variant === 'failed' && failedCardStyle),
    };
    
    return (
        <div style={cardStyle}>
            <div style={cardContentStyle}>
                {/* Status indicator */}
                {variant !== 'normal' && (
                    <StatusBadge status={status} />
                )}
                
                {/* Task title */}
                <span style={taskTitleStyle}>{task.title}</span>
                
                {/* Analyzing spinner */}
                {isAnalyzing && (
                    <span style={analyzingSpinnerStyle} title="AI is analyzing...">
                        ⟳
                    </span>
                )}
            </div>
            
            {/* Error message and retry button */}
            {isFailed && (
                <div style={errorContainerStyle}>
                    <span style={errorMessageStyle}>
                        {task.analysisError || 'Analysis failed'}
                    </span>
                    {onRetry && (
                        <button
                            onClick={onRetry}
                            style={retryButtonStyle}
                            title="Retry prioritization"
                        >
                            ↻ Retry
                        </button>
                    )}
                </div>
            )}
            
            {/* Polling attempts indicator (for debugging) */}
            {(task.pollingAttempts ?? 0) > 0 && variant === 'pending' && (
                <div style={attemptsStyle}>
                    Attempt {task.pollingAttempts}/15
                </div>
            )}
        </div>
    );
};

/**
 * Status badge component.
 */
const StatusBadge: React.FC<{ status: TaskAnalysisStatus | undefined }> = ({ status }) => {
    const label = getStatusLabel(status);
    
    const badgeStyle: React.CSSProperties = {
        ...baseBadgeStyle,
        ...(status === TaskAnalysisStatus.PENDING && pendingBadgeStyle),
        ...(status === TaskAnalysisStatus.ANALYZING && analyzingBadgeStyle),
        ...(status === TaskAnalysisStatus.FAILED && failedBadgeStyle),
        ...(status === TaskAnalysisStatus.TIMED_OUT && timedOutBadgeStyle),
    };
    
    return <span style={badgeStyle}>{label}</span>;
};

/**
 * Quadrant section of the matrix.
 */
interface QuadrantSectionProps {
    quadrant: Quadrant;
    tasks: Task[];
}

const QuadrantSection: React.FC<QuadrantSectionProps> = ({ quadrant, tasks }) => {
    const config = QUADRANT_CONFIG[quadrant];
    
    return (
        <div style={{ ...quadrantStyle, backgroundColor: config.color }}>
            <header style={quadrantHeaderStyle}>
                <h3 style={quadrantTitleStyle}>{config.title}</h3>
                <small style={quadrantSubtitleStyle}>{config.subtitle}</small>
            </header>
            
            <ul style={taskListStyle}>
                {tasks.length > 0 ? (
                    tasks.map(task => (
                        <li key={task.id} style={taskItemStyle}>
                            <span style={taskItemTitleStyle}>{task.title}</span>
                            {task.importance_score !== undefined && (
                                <span style={scoreStyle}>
                                    {Math.round((task.importance_score ?? 0) * 100)}%
                                </span>
                            )}
                        </li>
                    ))
                ) : (
                    <li style={emptyStateStyle}>No tasks</li>
                )}
            </ul>
        </div>
    );
};


// ---------------------------------------------------------------------------
// STYLES
// ---------------------------------------------------------------------------

// Container styles
const containerStyle: React.CSSProperties = {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto',
};

const headerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
};

// Polling indicator styles
const pollingIndicatorStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    backgroundColor: '#eff6ff',
    borderRadius: '20px',
    fontSize: '0.875rem',
    color: '#1d4ed8',
};

const spinnerStyle: React.CSSProperties = {
    display: 'inline-block',
    animation: 'spin 1s linear infinite',
};

// Pending section styles
const pendingSectionStyle: React.CSSProperties = {
    backgroundColor: '#fefce8',
    border: '1px solid #fef08a',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '20px',
};

const pendingHeaderStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    margin: '0 0 12px 0',
    fontSize: '1rem',
    color: '#854d0e',
};

const pendingIconStyle: React.CSSProperties = {
    fontSize: '1.2rem',
};

const pendingListStyle: React.CSSProperties = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
};

// Card styles
const baseCardStyle: React.CSSProperties = {
    padding: '12px 16px',
    borderRadius: '8px',
    backgroundColor: 'white',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    minWidth: '200px',
    maxWidth: '300px',
};

const pendingCardStyle: React.CSSProperties = {
    border: '1px solid #fef08a',
};

const failedCardStyle: React.CSSProperties = {
    border: '1px solid #fecaca',
    backgroundColor: '#fef2f2',
};

const cardContentStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
};

const taskTitleStyle: React.CSSProperties = {
    flex: 1,
    fontWeight: 500,
    color: '#374151',
};

const analyzingSpinnerStyle: React.CSSProperties = {
    display: 'inline-block',
    animation: 'spin 1s linear infinite',
    color: '#2563eb',
    fontSize: '1.2rem',
};

// Error styles
const errorContainerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: '8px',
    paddingTop: '8px',
    borderTop: '1px solid #fecaca',
};

const errorMessageStyle: React.CSSProperties = {
    fontSize: '0.75rem',
    color: '#dc2626',
    flex: 1,
};

const retryButtonStyle: React.CSSProperties = {
    padding: '4px 12px',
    fontSize: '0.75rem',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: 500,
};

const attemptsStyle: React.CSSProperties = {
    marginTop: '4px',
    fontSize: '0.7rem',
    color: '#9ca3af',
};

// Badge styles
const baseBadgeStyle: React.CSSProperties = {
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '0.7rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.025em',
};

const pendingBadgeStyle: React.CSSProperties = {
    backgroundColor: '#fef3c7',
    color: '#92400e',
};

const analyzingBadgeStyle: React.CSSProperties = {
    backgroundColor: '#dbeafe',
    color: '#1e40af',
};

const failedBadgeStyle: React.CSSProperties = {
    backgroundColor: '#fee2e2',
    color: '#dc2626',
};

const timedOutBadgeStyle: React.CSSProperties = {
    backgroundColor: '#f3e8ff',
    color: '#7c3aed',
};

// Matrix grid styles
const matrixGridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gridTemplateRows: '1fr 1fr',
    gap: '16px',
    minHeight: '500px',
};

// Quadrant styles
const quadrantStyle: React.CSSProperties = {
    padding: '16px',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
};

const quadrantHeaderStyle: React.CSSProperties = {
    marginBottom: '12px',
};

const quadrantTitleStyle: React.CSSProperties = {
    margin: 0,
    fontSize: '1rem',
    fontWeight: 600,
};

const quadrantSubtitleStyle: React.CSSProperties = {
    color: '#6b7280',
    fontSize: '0.8rem',
};

// Task list styles
const taskListStyle: React.CSSProperties = {
    listStyle: 'none',
    padding: 0,
    margin: 0,
    flex: 1,
    overflowY: 'auto',
};

const taskItemStyle: React.CSSProperties = {
    padding: '10px 12px',
    marginBottom: '6px',
    backgroundColor: 'rgba(255, 255, 255, 0.7)',
    borderRadius: '6px',
    fontSize: '0.9rem',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
};

const taskItemTitleStyle: React.CSSProperties = {
    flex: 1,
};

const scoreStyle: React.CSSProperties = {
    fontSize: '0.75rem',
    color: '#6b7280',
    backgroundColor: 'rgba(0,0,0,0.05)',
    padding: '2px 6px',
    borderRadius: '4px',
};

const emptyStateStyle: React.CSSProperties = {
    padding: '20px',
    textAlign: 'center',
    color: '#9ca3af',
    fontStyle: 'italic',
    fontSize: '0.9rem',
};


// ---------------------------------------------------------------------------
// CSS KEYFRAMES (inject into document)
// ---------------------------------------------------------------------------

// Add keyframe animation for spinner
if (typeof document !== 'undefined') {
    const styleId = 'prioritization-matrix-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
}


export default PrioritizationMatrix;
