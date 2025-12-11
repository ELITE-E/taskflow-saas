// /src/components/auth/AuthFormWrapper.tsx (Client Component)

import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { FieldValue, FieldValues, UseFormReturn } from 'react-hook-form';
import React from 'react';

interface AuthFormWrapperProps<TFormValues> {
  form: UseFormReturn<TFormValues extends FieldValues? TFormValues:FieldValues>;
  onSubmit: (values: TFormValues) => void;
  submitText: string;
  children: React.ReactNode;
}

// Generic function component to handle form submission boilerplate
export const AuthFormWrapper = <TFormValues,>({
  form,
  onSubmit,
  submitText,
  children,
}: AuthFormWrapperProps<TFormValues>) => {
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-4">
        {children}
        <Button 
            type="submit" 
            className="w-full" 
            disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? `${submitText}...` : submitText}
        </Button>
      </form>
    </Form>
  );
};