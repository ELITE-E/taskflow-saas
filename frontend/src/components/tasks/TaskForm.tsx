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

/**
 * STRICT front-end contract: payload must be exactly:
 * { title, description, due_date, effort_estimate }
 *
 * Effort is a bounded relative integer 1..5 (NOT hours).
 */

// Zod schema validates exactly the fields the backend expects.
const TaskSchema = z.object({
  title: z.string().min(1, "Title is required.").max(255),
  description: z.string().min(1, "Description is required.").max(2000),
  // date: nullable YYYY-MM-DD string (or null)
  due_date: z.preprocess((val) => {
    if (val === '' || val === undefined || val === null) return null;
    return String(val);
  }, z.string().nullable().optional()),
  // Effort: integer 1..5. Accept string input but coerce safely to integer.
  effort_estimate: z.preprocess((val) => {
    if (typeof val === 'string') {
      const n = Number(val);
      return Number.isFinite(n) ? Math.round(n) : val;
    }
    return val;
  }, z.number().int().min(1).max(10)),
});

type TaskFormValues = z.infer<typeof TaskSchema>;

export default function TaskForm() {
  const dispatch = useDispatch<AppDispatch>();
  const form = useForm<TaskFormValues>({
    resolver: zodResolver(TaskSchema),
    defaultValues: {
      title: '',
      description: '',
      due_date: null,
      effort_estimate: 3,
    },
  });

  const loading = form.formState.isSubmitting;

  const onSubmit = async (values: TaskFormValues) => {
    // Honest payload: exactly the keys backend expects.
    const payload = {
      title: values.title,
      description: values.description,
      due_date: values.due_date ?? null,
      effort_estimate: Number(values.effort_estimate),
    };

    const result = await dispatch(addTask(payload as any));

    if (addTask.fulfilled.match(result)) {
      form.reset({ title: '', description: '', due_date: null, effort_estimate: 3 });
    }
    // Do not wait for AI results; backend will update task when ready.
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Plus className="w-5 h-5 text-indigo-600" />
          <span>Add New Task</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* Title */}
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Short task title" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Description */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input placeholder="Describe the task" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Due date */}
            <FormField
              control={form.control}
              name="due_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    Due Date
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      {...field}
                      value={field.value ?? ''}
                      onChange={(e) => field.onChange(e.target.value || '')}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Effort */}
            <FormField
              control={form.control}
              name="effort_estimate"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Effort (1–10, relative difficulty)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      step={1}
                      {...field}
                      value={field.value ?? ''}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <p className="text-sm text-gray-500">Effort is a relative estimate, not hours.</p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button type="submit" disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Add Task'}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}