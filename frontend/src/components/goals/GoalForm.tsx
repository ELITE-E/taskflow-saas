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
  weight: z.number().min(1, "Must be 1-10.").max(10, "Must be 1-10.").default(5),
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
                    {/* Convert string input to number for Zod validation */}
                    <Input 
                        type="number" 
                        placeholder="5" 
                        min={1} 
                        max={10}
                        {...field} 
                        onChange={event => field.onChange(parseInt(event.target.value))}
                    />
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