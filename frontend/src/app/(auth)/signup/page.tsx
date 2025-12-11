'use client';

import { GalleryVerticalEnd } from "lucide-react"
import { SignupForm } from "@/components/signup-form"
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useRouter } from 'next/navigation';
import { useDispatch } from 'react-redux';
import { AuthCard } from '@/components/auth/AuthCard';
import { AuthFormWrapper } from '@/components/auth/AuthFormWrapper';
import { FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { handleRegister } from '@/lib/auth-api';

// 1. Define Zod schema
const SignupSchema = z.object({
    username: z.string().min(3, { message: "Username must be at least 3 characters." }),
    email: z.string().email({ message: "Invalid email address." }),
    first_name: z.string().min(1, { message: "First name is required." }),
    last_name: z.string().min(1, { message: "Last name is required." }),
    password: z.string().min(8, { message: "Password must be at least 8 characters." }),
    password2: z.string().min(8, { message: "Confirm password must match." }),
}).refine((data) => data.password === data.password2, {
    message: "Passwords do not match.",
    path: ["password2"],
});

type SignupValues = z.infer<typeof SignupSchema>;

export default function SignupPage() {
  const router = useRouter();
  const dispatch = useDispatch();
  
  const form = useForm<SignupValues>({
    resolver: zodResolver(SignupSchema),
    defaultValues: { username: '', email: '', first_name: '', last_name: '', password: '', password2: '' },
  });

  const onSubmit = async (values: SignupValues) => {
    // handleRegister attempts auto-login on success
    await handleRegister(values, dispatch, router);
  };

  return (
    <AuthCard 
      title="Create Account" 
      description="Enter your details to create your prioritizer account." 
      isLogin={false}
    >
      <AuthFormWrapper 
        form={form} 
        onSubmit={onSubmit} 
        submitText="Signing Up"
      >
        <div className="grid grid-cols-2 gap-4">
            {/* Input fields for First Name, Last Name, Email, Username, Password, Password2 */}
            <FormField control={form.control} name="first_name" render={({ field }) => (
                <FormItem><FormLabel>First Name</FormLabel><FormControl><Input placeholder="John" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="last_name" render={({ field }) => (
                <FormItem><FormLabel>Last Name</FormLabel><FormControl><Input placeholder="Doe" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
        </div>
        <FormField control={form.control} name="email" render={({ field }) => (
            <FormItem><FormLabel>Email</FormLabel><FormControl><Input placeholder="john.doe@email.com" {...field} /></FormControl><FormMessage /></FormItem>
        )} />
        <FormField control={form.control} name="username" render={({ field }) => (
            <FormItem><FormLabel>Username</FormLabel><FormControl><Input placeholder="john_doe" {...field} /></FormControl><FormMessage /></FormItem>
        )} />
        <FormField control={form.control} name="password" render={({ field }) => (
            <FormItem><FormLabel>Password</FormLabel><FormControl><Input type="password" placeholder="********" {...field} /></FormControl><FormMessage /></FormItem>
        )} />
        <FormField control={form.control} name="password2" render={({ field }) => (
            <FormItem><FormLabel>Confirm Password</FormLabel><FormControl><Input type="password" placeholder="********" {...field} /></FormControl><FormMessage /></FormItem>
        )} />
      </AuthFormWrapper>
    </AuthCard>
  );
}

export  function Signup() {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex justify-center gap-2 md:justify-start">
          <a href="#" className="flex items-center gap-2 font-medium">
            <div className="bg-primary text-primary-foreground flex size-6 items-center justify-center rounded-md">
              <GalleryVerticalEnd className="size-4" />
            </div>
            Acme Inc.
          </a>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">
            <SignupForm />
          </div>
        </div>
      </div>
      <div className="bg-muted relative hidden lg:block">
        <img
          src="/placeholder.svg"
          alt="Image"
          className="absolute inset-0 h-full w-full object-cover dark:brightness-[0.2] dark:grayscale"
        />
      </div>
    </div>
  )
}
