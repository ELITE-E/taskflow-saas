// /src/app/page.tsx (Use Client Component)

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '@/redux/store';
import { useAuthCheck } from '@/hooks/useAuthCheck'; // Import the new hook
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function RootPage() {
  const router = useRouter();
  
  // 1. Run the initial authentication check on mount
  useAuthCheck(); 

  // 2. Select state from Redux
  const { isAuthenticated, loading } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    // Wait until the authentication check is complete
    if (!loading) {
      if (isAuthenticated) {
        // Redirection on success
        router.replace('/home');
      } else {
        // Redirection on failure/unauthenticated
        router.replace('/login');
      }
    }
  }, [isAuthenticated, loading, router]);

  // 3. UI while loading
  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="mt-4 text-gray-600">Checking session...</span>
      </div>
    );
  }

  // 4. Fallback/Unauthenticated Landing View (Optional, if you prefer a landing page over direct redirect)
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-6 text-center">
      <h1 className="text-4xl font-bold text-gray-800">Prioritize Your Life</h1>
      <p className="mt-3 text-lg text-gray-600">
        The AI-Powered Eisenhower Matrix helps you stop reacting and start achieving.
      </p>
      <div className="mt-8 space-x-4">
        <Button onClick={() => router.push('/login')}>Sign In</Button>
        <Button variant="outline" onClick={() => router.push('/signup')}>Create Account</Button>
      </div>
    </div>
  );
}