 'use client';
 import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
 import { getPrioritizedTasks, completeTask, removeTask } from '@/redux/slices/tasksSlice';
import { RootState, AppDispatch } from '@/redux/store';
 import { Button } from '@/components/ui/button';
 import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
 import { Check, Loader2, Calendar, Trash2 } from 'lucide-react';
 
 export default function TaskList() {
   const dispatch = useDispatch<AppDispatch>();
   const { tasks, loading, error } = useSelector((state: RootState) => state.tasks);
   // Fetch tasks when the component mounts
   useEffect(() => {
     dispatch(getPrioritizedTasks());
   }, [dispatch]);
   const handleComplete = (taskId: number) => {
     dispatch(completeTask(taskId));
   };
   const handleDelete = (taskId: number) => {
     if (confirm("Are you sure you want to permanently delete this task?")) {
       dispatch(removeTask(taskId));
     }
   };
   if (loading) {
     return (
       <div className="flex justify-center items-center h-40">
         <Loader2 className="mr-2 h-6 w-6 animate-spin" />
         <p>Loading your active tasks...</p>
       </div>
     );
   }
   if (error) {
     return <p className="text-red-500">Error loading tasks: {error}</p>;
   }
   const formatDate = (dateString: string | null) => {
     if (!dateString) return 'No Due Date';
     return new Date(dateString).toLocaleDateString();
   }
   return (
     <div className="space-y-4">
       <h2 className="text-2xl font-semibold flex items-center space-x-2 text-gray-700">
           <Check className="w-6 h-6 text-green-600" />
           <span>Active Tasks ({tasks.length})</span>
       </h2>
 
       {tasks.length === 0 ? (
         <Card className="p-6 border-dashed text-center">
             <p className="text-gray-500">No active tasks. Time to add some!</p>
         </Card>
       ) : (
         <div className="space-y-3">
           {tasks.map((task) => (
             <div key={task.id} className="flex items-center bg-white p-3 rounded-lg shadow-sm border border-gray-100 transition-all hover:shadow-md">
           
                 {/* Completion Button (Check/Swipe) */}
                 <Button
                     variant="ghost"
                     size="icon"
                     onClick={() => handleComplete(task.id)}
                     className="shrink-0 text-green-500 hover:bg-green-50"
                     title="Mark as Complete"
                 >
                     <Check className="w-5 h-5" />
                 </Button>
                 {/* Task Content */}
                 <div className="grow ml-3">
                     <CardTitle className="text-base font-medium">{task.title}</CardTitle>
                     <div className="text-xs text-gray-500 flex items-center space-x-2 mt-0.5">
                         <Calendar className="w-3 h-3"/>
                         <span>Due: {formatDate(task.due_date)}</span>
                     </div>
                 </div>
                 {/* Delete Button */}
                 <Button
                     variant="ghost"
                     size="icon"
                     onClick={() => handleDelete(task.id)}
                     className="shrink-0 text-red-400 hover:text-red-600"
                     title="Delete Task"
                 >
                     <Trash2 className="w-4 h-4" />
                 </Button>
             </div>
           ))}
         </div>
       )}
     </div>
   );
 }

//c/components/tasks/TaskList.tsx
//port { TaskItem } from "./TaskItem";
//port{Task} from '@/types/tasks'
//port const TaskList = () => {
//   const { tasks } = useSelector((state: RootState) => state.tasks);

//   return (
//     <div className="bg-white rounded shadow">
//       {tasks.map(task => (
//         <TaskItem key={task.id} task={task} />
//       ))}
//     </div>
//   );
// };