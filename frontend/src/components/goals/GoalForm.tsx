// /src/components/goals/GoalForm.tsx

'use client';

import * as z from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@/redux/store';
import { addGoal } from '@/redux/slices/goalsSlice';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Loader2, PlusCircle } from 'lucide-react';

// Define Zod schema for validation
const GoalSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters.").max(255),
  description: z.string().min(10, "Description must be detailed.").max(1000),
  // Preprocess incoming values: convert string -> number (handles empty string too)
  weight: z.preprocess((val) => {
    if (typeof val === 'string') {
      // empty string -> undefined so required/default behavior remains consistent
      return val === '' ? undefined : Number(val);
    }
    return val;
  }, z.number().min(1, "Must be 1-10.").max(10, "Must be 1-10.").default(5)),
  // Category field: simple validated string. Adjust allowed values if you have fixed categories.
  category: z.string().min(1, "Select a category").max(100, "Category name too long").default('General'),
});

type GoalFormValues = z.infer<typeof GoalSchema>;

export default function GoalForm() {
  const dispatch = useDispatch<AppDispatch>();
  const loading = useSelector((state: RootState) => state.goals.loading);
  
  const form = useForm<GoalFormValues>({
    resolver: zodResolver(GoalSchema),
    defaultValues: {
      title: "",
      description: "",
      weight: 5,
      category: 'General',
    },
  });

  const onSubmit = async (values: GoalFormValues) => {
    // Dispatch the thunk to create a new goal
    const result = await dispatch(addGoal(values));
    
    // Check if the creation was successful and reset the form
    if (addGoal.fulfilled.match(result)) {
      form.reset(); // Clear the form fields
      alert('Goal created successfully!');
    }
    // Error handling is managed by the Redux slice (though we could display a toast here)
  };

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center space-x-2"><PlusCircle className="w-5 h-5 text-green-600" /><span>Create New Goal</span></CardTitle></CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            
            {/* Title Field */}
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Goal Title</FormLabel>
                  <FormControl><Input placeholder="e.g., Launch MVP" {...field} /></FormControl>
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
                  <FormLabel>Detailed Description</FormLabel>
                  <FormControl><Textarea rows={4} placeholder="What specifically does this goal involve?" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* Weight Field */}
            <FormField
              control={form.control}
              name="weight"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Strategic Weight (1-10)</FormLabel>
                  <FormControl>
                    {/* Ensure the controller receives a number */}
                    <Input 
                        type="number" 
                        placeholder="5" 
                        min={1} 
                        max={10}
                        {...field} 
                        value={field.value ?? ''}
                        onChange={event => field.onChange(Number(event.target.value))}
                    />
                  </FormControl>
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
                  <FormControl>
                    <select
                      {...field}
                      className="w-full rounded border px-3 py-2"
                      value={field.value}
                      onChange={e => field.onChange(e.target.value)}
                    >
                      <option value="General">General</option>
                      <option value="Work">Work</option>
                      <option value="Personal">Personal</option>
                      <option value="Health">Health</option>
                      <option value="Study">Study</option>
                      <option value="Relationships">Relationships</option>
                      <option value="Other">Other</option>
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button type="submit" disabled={loading}>
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                'Save Goal'
              )}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}