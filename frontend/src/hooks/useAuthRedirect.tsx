// /src/hooks/useAuthRedirect.ts

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '@/redux/store';

/**
 * Hook to redirect authenticated users away from auth pages (/login, /signup).
 * Relies on the global Redux state updated by useAuthCheck on initial load.
 */
export const useAuthRedirect = () => {
    const router = useRouter();
    // Get the core authentication status from Redux
    const { isAuthenticated, loading } = useSelector((state: RootState) => state.auth);

    useEffect(() => {
        // 1. Must wait until the loading check is complete (i.e., tokens have been checked)
        if (!loading) {
            // 2. If the user is authenticated, redirect them out of the (auth) route group
            if (isAuthenticated) {
                router.replace('/home');
            }
        }
    }, [isAuthenticated, loading, router]);
    
    // Returns the loading state so the layout can display a spinner while deciding.
    return { loading, isAuthenticated };
};