// /src/app/home/page.tsx (CORRECTED)

'use client';

import { useSelector, useDispatch } from 'react-redux';
import { useRouter } from 'next/navigation';
import { RootState } from '@/redux/store';
import { handleLogout } from '@/lib/auth-api';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LogOut, User } from 'lucide-react';
import { useEffect } from 'react'; 
import GoalForm from '@/components/goals/GoalForm';
import GoalList from '@/components/goals/GoalList';
import TaskForm from '@/components/tasks/TaskForm';
import TaskList from '@/components/tasks/TaskList';
import PrioritizationMatrix from '@/components/tasks/PrioritizationMatrix';
//import { useTaskPolling } from '@/hooks/useTaskPolling';
export default function HomePage() {
  const dispatch = useDispatch();
  const router = useRouter();
  
  const { user, isAuthenticated, loading } = useSelector((state: RootState) => state.auth);

  // 1. FIX: Move redirect logic into useEffect
  useEffect(() => {
    // Only attempt redirection once loading check is complete
    if (!loading && !isAuthenticated) {
        // Use replace to prevent back button access to the page 
        // if the user is somehow unauthenticated here.
        router.replace('/login');
    }
  }, [loading, isAuthenticated, router]); // Dependency array includes router, loading, and auth state

  const onLogout = () => {
    handleLogout(dispatch, router);
  };

  // 2. Handle Loading/Unauthenticated State (Render a minimal UI)
  if (loading || !isAuthenticated || !user) {
    // Return a spinner or null while the useEffect logic runs and redirects
    return (
        <div className="flex min-h-screen items-center justify-center">
            <p>Accessing Dashboard...</p> 
        </div>
    );
  }
//useTaskPolling()
  // 3. Render Dashboard Content (Only runs if isAuthenticated is true)
  return (
    // <div className="flex min-h-screen bg-gray-50 p-8">
    //   <div className="w-full max-w-4xl mx-auto space-y-8">
        
    //     {/* Header/Greeting Section */}
    //     <header className="py-6 border-b border-gray-200 flex justify-between items-center">
    //         <h1 className="text-3xl font-bold text-gray-800">
    //             Welcome, {user.first_name || user.username}!
    //         </h1>
    //         <Button onClick={onLogout} variant="outline" className="flex items-center space-x-2">
    //             <LogOut className="w-4 h-4" />
    //             <span>Logout</span>
    //         </Button>
    //     </header>

    //     {/* User Profile Card */}
    //     <Card className="w-full">
    //         <CardHeader>
    //             <CardTitle className="flex items-center space-x-2">
    //                 <User className="w-5 h-5" />
    //                 <span>Authentication Confirmed</span>
    //             </CardTitle>
    //             <CardDescription>
    //                 This is your dashboard. All future content related to Goals and Tasks will appear here.
    //             </CardDescription>
    //         </CardHeader>
    //         <CardContent className="space-y-3">
    //             <p><strong>Email:</strong> {user.email}</p>
    //             <p><strong>Username:</strong> {user.username}</p>
    //             <p><strong>Status:</strong> <span className="text-green-600 font-medium">Authenticated</span></p>
    //         </CardContent>
    //     </Card>
        
    //     {/* Core Application Section (Placeholder) */}
    //     <section className="p-6 border rounded-lg bg-white shadow-sm">
    //         <h2 className="text-2xl font-semibold text-gray-700">Your Prioritization Hub</h2>
    //         <p className="mt-2 text-gray-600">
    //             Next up: We will build the Django `goals` and `tasks` apps to populate this area with your data!
    //         </p>
    //     </section>

    //   </div>
    // </div>
    <div className="flex min-h-screen bg-gray-50 p-8">
      <div className="w-full max-w-6xl mx-auto space-y-8">
        
        {/* Header Section (Greeting & Logout Button) */}
        <header className="py-6 border-b border-gray-200 flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-800">
                Welcome, {user.first_name || user.username}!
            </h1>
            <Button onClick={onLogout} variant="outline" className="flex items-center space-x-2">
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
            </Button>
        </header>

        <main className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* COLUMN 1: Task Management (Input & List) */}
            <div className="space-y-8">
                <TaskForm />
                <GoalForm />
            </div>

            {/* COLUMN 2: Goal Management (Form & List) 
            
            <GoalList />
            */}
            <div className="space-y-8">
                <TaskList />
                <PrioritizationMatrix/>
            </div>

        </main>

      </div>
    </div>
  );
}