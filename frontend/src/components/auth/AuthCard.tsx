// /src/components/auth/AuthCard.tsx (Client Component)

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import Link from 'next/link';
import React from 'react';

/**
 * Description:Ageneric component for card structure and navigation link
 */
interface AuthCardProps {
  title: string;
  description: string;
  children: React.ReactNode;
  isLogin?: boolean; // True for Login, False for Signup
}

export const AuthCard: React.FC<AuthCardProps> = ({ title, description, children, isLogin = true }) => {
  const switchUrl = isLogin ? '/signup' : '/login';
  const switchText = isLogin ? "Don't have an account?" : "Already have an account?";
  const switchLinkText = isLogin ? "Sign up" : "Sign in";

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          {children}
          <p className="mt-4 text-center text-sm text-muted-foreground">
            {switchText}{' '}
            <Link href={switchUrl} className="underline hover:text-primary">
              {switchLinkText}
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
};