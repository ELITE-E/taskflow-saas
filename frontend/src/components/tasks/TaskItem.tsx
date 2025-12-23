// src/components/tasks/TaskItem.tsx
import React from 'react';
import { Task } from '@/types/tasks';

export const TaskItem = ({ task }: { task: Task }) => {
  return (
    <div className="task-item p-4 border-b flex items-center justify-between">
      <div>
        <h3 className={`font-medium ${!task.is_prioritized ? 'text-gray-400' : 'text-gray-900'}`}>
          {task.title}
        </h3>
        
        {/* SPECIFIC UX REFINEMENT LOCATION */}
        {!task.is_prioritized ? (
          <div className="flex items-center mt-1 text-xs font-semibold text-amber-600 animate-pulse">
            <Brain className="w-3 h-3 mr-1" />
            AI Categorizing...
          </div>
        ) : (
          <div className="flex items-center mt-1 text-xs text-gray-500">
            <Clock className="w-3 h-3 mr-1" />
            Priority Score: {Math.round(task.priority_score * 100)}
          </div>
        )}
      </div>

      <div className="flex items-center space-x-2">
        {/* Disable actions while processing to prevent data conflicts */}
        <button disabled={!task.is_prioritized} className="disabled:opacity-30">
          <CheckCircle className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};