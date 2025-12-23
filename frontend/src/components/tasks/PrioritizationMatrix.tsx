import React from 'react';
import { useSelector } from 'react-redux';
import { selectPrioritizedTasks} from '../../redux/slices/tasksSlice';
import { Task } from '@/types/tasks';

/**
 * Types for the grouped quadrant structure
 */
interface GroupedTasks {
  Q1: Task[];
  Q2: Task[];
  Q3: Task[];
  Q4: Task[];
}

/**
 * Visualizes tasks in the Eisenhower Matrix (Q1-Q4)
 */
const PrioritizationMatrix: React.FC = () => {
  const tasks = useSelector(selectPrioritizedTasks);

  // Group tasks by their quadrant field
  const grouped: GroupedTasks = tasks.reduce(
    (acc, task) => {
      if (task.quadrant in acc) {
        acc[task.quadrant as keyof GroupedTasks].push(task);
      }
      return acc;
    },
    { Q1: [], Q2: [], Q3: [], Q4: [] } as GroupedTasks
  );

  return (
    <div className="prioritization-matrix">
      <h2>Strategic Task Matrix</h2>
            
      <div className="matrix-grid" style={matrixGridStyle}>
        <QuadrantSection 
          title="DO NOW" 
          subtitle="Urgent & Important" 
          tasks={grouped.Q1} 
          color="#fee2e2" 
        />
        <QuadrantSection 
          title="SCHEDULE" 
          subtitle="Not Urgent & Important" 
          tasks={grouped.Q2} 
          color="#fef3c7" 
        />
        <QuadrantSection 
          title="DELEGATE" 
          subtitle="Urgent & Not Important" 
          tasks={grouped.Q3} 
          color="#dcfce7" 
        />
        <QuadrantSection 
          title="DELETE / DROP" 
          subtitle="Not Urgent & Not Important" 
          tasks={grouped.Q4} 
          color="#f3f4f6" 
        />
      </div>
    </div>
  );
};

interface QuadrantProps {
  title: string;
  subtitle: string;
  tasks: Task[];
  color: string;
}

const QuadrantSection: React.FC<QuadrantProps> = ({ title, subtitle, tasks, color }) => (
  <div style={{ ...quadrantStyle, backgroundColor: color }}>
    <header>
      <h3 style={{ margin: 0 }}>{title}</h3>
      <small>{subtitle}</small>
    </header>
    <ul style={listStyle}>
      {tasks.length > 0 ? (
        tasks.map((task) => (
          <li key={task.id} style={itemStyle}>
            {task.title}
          </li>
        ))
      ) : (
        <li style={{ ...itemStyle, color: '#6b7280', fontStyle: 'italic' }}>No tasks</li>
      )}
    </ul>
  </div>
);

/**
 * Simple internal styles for layout
 */
const matrixGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gridTemplateRows: '1fr 1fr',
  gap: '16px',
  marginTop: '20px',
  minHeight: '500px'
};

const quadrantStyle: React.CSSProperties = {
  padding: '16px',
  borderRadius: '8px',
  border: '1px solid #e5e7eb',
  display: 'flex',
  flexDirection: 'column'
};

const listStyle: React.CSSProperties = {
  listStyle: 'none',
  padding: 0,
  marginTop: '12px'
};

const itemStyle: React.CSSProperties = {
  padding: '8px',
  marginBottom: '4px',
  backgroundColor: 'rgba(255, 255, 255, 0.6)',
  borderRadius: '4px',
  fontSize: '0.9rem',
  boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
};

export default PrioritizationMatrix;