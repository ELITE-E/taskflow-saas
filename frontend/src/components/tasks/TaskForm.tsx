// /src/components/tasks/TaskForm.tsx

'use client';

import * as z from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '@/redux/store';
import { addTask } from '@/redux/slices/tasksSlice';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Calendar, Loader2, Plus } from 'lucide-react';

const TaskSchema = z.object({
  title: z.string().min(1, "Title is required.").max(255),
  description: z.string().min(1, "Description is required.").max(255),

  // Date input usually comes as a string in YYYY-MM-DD format
  due_date: z.string().nullable().optional(), 
  effort_hours: z.string().min(1, "Effort in hours is required.").max(255),
  category: z.string().min(1, "Category is required.").max(255),
});

type TaskFormValues = z.infer<typeof TaskSchema>;

export default function TaskForm() {
  const dispatch = useDispatch<AppDispatch>();
  const form = useForm<TaskFormValues>({
    resolver: zodResolver(TaskSchema),
    defaultValues: { title: "", due_date: null },
  });
  
  const loading = form.formState.isSubmitting;

  const onSubmit = async (values: TaskFormValues) => {
    // Dispatch the thunk to create a new task
    const payload = {
        ...values,
        // Ensure due_date is sent as null if empty string
        due_date: values.due_date || null
    };

    const result = await dispatch(addTask(payload));
    
    if (addTask.fulfilled.match(result)) {
      form.reset({ title: "", due_date: null }); // Reset form
    }
  };

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center space-x-2"><Plus className="w-5 h-5 text-indigo-600" /><span>Add New Task</span></CardTitle></CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            
            {/* Title Field */}
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Task Title</FormLabel>
                  <FormControl><Input placeholder="e.g., Pay electricity and internet bills" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

              {/* Description Field */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel> Description</FormLabel>
                  <FormControl><Input placeholder="e.g., Services my be cut" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Due Date Field */}
            <FormField
              control={form.control}
              name="due_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center"><Calendar className="w-4 h-4 mr-1"/>Due Date</FormLabel>
                  <FormControl><Input type="date" {...field} value={field.value || ''} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

              {/* EffortField */}
            <FormField
              control={form.control}
              name="effort_hours"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Effort in Hours</FormLabel>
                  <FormControl><Input placeholder="e.g., 0.5" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

              {/* Category Field */}
            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Category</FormLabel>
                  <FormControl><Input placeholder="e.g., Work, Personal, Bills etc." {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button type="submit" disabled={loading}>
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                'Add Task'
              )}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}