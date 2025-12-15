// /src/components/tasks/PrioritizationMatrix.tsx

'use client';

import { useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getPrioritizedTasks, completeTask } from '@/redux/slices/tasksSlice';
import { RootState, AppDispatch } from '@/redux/store';
import { Task } from '@/types/tasks';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Check, Target, Calendar } from 'lucide-react';

// --- UTILITY FUNCTIONS ---

const isUrgent = (task: Task): boolean => {
  // Define urgency as due in the next 3 days OR past due
  if (!task.due_date) return false;
  const daysUntilDue = (new Date(task.due_date).getTime() - new Date().getTime()) / (1000 * 3600 * 24);
  return daysUntilDue <= 3;
};

const isImportant = (task: Task): boolean => {
  // Define importance based on Goal Weight (e.g., weight 6 or higher is important)
  return (task.goal_weight || 1) >= 6;
};

// Determines the Quadrant based on Urgency and Importance
const getQuadrant = (task: Task) => {
  const urgent = isUrgent(task);
  const important = isImportant(task);

  if (urgent && important) return 'Do';
  if (!urgent && important) return 'Decide';
  if (urgent && !important) return 'Delegate';
  return 'Delete/Defer';
};

// --- SUB-COMPONENT: Task Card in the Matrix ---

const MatrixTaskCard: React.FC<{ task: Task, onComplete: (id: number) => void }> = ({ task, onComplete }) => (
    <div className="flex items-start justify-between bg-white p-2 rounded-md border border-gray-100 shadow-xs hover:shadow-sm transition-shadow">
        <div className="grow">
            <p className="text-sm font-medium leading-tight">{task.title}</p>
            <div className="text-xs text-gray-500 mt-1 flex items-center space-x-2">
                {task.due_date && <span className="flex items-center"><Calendar className="w-3 h-3 mr-1"/>{new Date(task.due_date).toLocaleDateString()}</span>}
                {task.goal_weight && <span className="flex items-center"><Target className="w-3 h-3 mr-1"/>W: {task.goal_weight}</span>}
            </div>
            <p className="text-xs text-indigo-500 mt-1">Score: {task.priority_score.toFixed(2)}</p>
        </div>
        <Button
            variant="ghost"
            size="icon"
            onClick={() => onComplete(task.id)}
            className="shrink-0 text-green-500 hover:bg-green-50 w-8 h-8 ml-2"
            title="Mark as Complete"
        >
            <Check className="w-4 h-4" />
        </Button>
    </div>
);


// --- MAIN COMPONENT: Prioritization Matrix ---

export default function PrioritizationMatrix() {
  const dispatch = useDispatch<AppDispatch>();
  const { tasks, loading, error } = useSelector((state: RootState) => state.tasks);

  useEffect(() => {
    // Fetch prioritized tasks on mount
    dispatch(getPrioritizedTasks());
  }, [dispatch]);

  const handleComplete = (taskId: number) => {
    dispatch(completeTask(taskId));
  };

  // Use useMemo to categorize tasks once when the tasks array changes
  const categorizedTasks = useMemo(() => {
    const categories: Record<string, Task[]> = {
      Do: [],
      Decide: [],
      Delegate: [],
      'Delete/Defer': [],
    };

    tasks.forEach(task => {
      const quadrant = getQuadrant(task);
      categories[quadrant].push(task);
    });
    return categories;
  }, [tasks]);

  const quadrants = [
    { name: 'Do', color: 'bg-red-100', title: '🔴 Urgent & Important (Highest Score)' },
    { name: 'Decide', color: 'bg-yellow-100', title: '🟡 Not Urgent & Important' },
    { name: 'Delegate', color: 'bg-blue-100', title: '🔵 Urgent & Not Important' },
    { name: 'Delete/Defer', color: 'bg-gray-100', title: '⚪ Not Urgent & Not Important (Lowest Score)' },
  ];

  if (loading) {
    return <div className="text-center p-8"><Loader2 className="h-8 w-8 animate-spin mx-auto text-indigo-500" /></div>;
  }
  if (error) {
    return <p className="text-red-500 p-4">Error loading prioritized tasks: {error}</p>;
  }

  // --- MATRIX RENDER ---
  return (
    <div className="space-y-6">
      <CardHeader>
        <CardTitle className="text-2xl text-gray-800">
            Task Prioritization Matrix 

[Image of a Task Prioritization Matrix]

        </CardTitle>
        <p className="text-gray-500">Tasks are sorted by AI score and categorized by Urgency (Due Date) and Importance (Goal Weight).</p>
      </CardHeader>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {quadrants.map(({ name, color, title }) => (
          <Card key={name} className={`p-0 ${color} shadow-lg`}>
            <CardHeader className={`py-3 px-4 border-b border-${color.split('-')[1]}-300`}>
              <CardTitle className="text-lg">{title} ({categorizedTasks[name].length})</CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-3 min-h-[200px] max-h-[50vh] overflow-y-auto">
              {categorizedTasks[name].length > 0 ? (
                // Display tasks sorted by the backend's priority_score
                categorizedTasks[name].map(task => (
                  <MatrixTaskCard key={task.id} task={task} onComplete={handleComplete} />
                ))
              ) : (
                <p className="text-sm text-gray-600 italic mt-4">No tasks in this quadrant.</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}