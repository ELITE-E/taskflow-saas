// /src/app/(auth)/layout.tsx

'use client'; // Must be a Client Component to use Redux and hooks

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Loader2 } from 'lucide-react';
import { useAuthRedirect } from '@/hooks/useAuthRedirect';

const AuthLayout = ({ children }: { children : React.ReactNode }) => {
    
    // Run the redirection logic
    const { loading, isAuthenticated } = useAuthRedirect(); 

    
    // RENDER: Check 1 (Loading State)
    // If we are still checking for tokens, show a full-page spinner 
    // to prevent the flicker of the login page before redirecting.
    if (loading || isAuthenticated) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-2 text-gray-600">Checking session...</span>
            </div>
        );
    }
    // --------------------------------------------------------
    
    // RENDER: Check 2 (Unauthenticated State)
    // If not loading and not authenticated, render the login/signup content
    return (
        // Use flex layout to mimic the two-column structure (Auth left, Testimonial right)
        <main className="flex min-h-screen">
            
            {/* --- Left Section: Auth Form --- */}
            <section className="flex-1 flex flex-col items-center justify-center p-8 lg:p-12">
                <div className="w-full max-w-md flex flex-col flex-1">
                    
                    {/* Placeholder Logo Link */}
                    <div className="mb-8 mt-4">
                        <Link href="/" className="text-xl font-bold text-primary">
                            <span className="text-2xl font-extrabold text-blue-600">Prioritizer</span>
                        </Link>
                    </div>

                    {/* Children (Login/Signup Page Content) */}
                    <div className="flex-1 flex flex-col justify-center">
                        {children}
                    </div>
                </div>
            </section>

            {/* --- Right Section: Marketing/Testimonial (Hidden on small screens) --- */}
            <section className="hidden lg:flex w-1/2 bg-gray-900 relative items-center justify-center p-12 text-white">
                <div className="absolute inset-0 bg-cover bg-center opacity-30" 
                     style={{backgroundImage: 'url(/assets/images/dashboard.png)'}} 
                />
                <div className="z-10 relative max-w-md">
                    <blockquote className="text-2xl italic font-light leading-relaxed border-l-4 border-blue-400 pl-4">
                         "The AI-Powered Matrix helped me stop reacting to Q3 tasks and finally focus on Q2 strategy. It's truly bias-eliminating."
                    </blockquote>
                    <footer className="mt-4 text-sm">
                        <cite>- Productive User</cite>
                        <div className="flex mt-1">
                            {/* Star Rating Placeholder */}
                            {[1, 2, 3, 4, 5].map((star) => (
                                <span key={star} className="text-yellow-400">★</span>
                            ))}
                        </div>
                    </footer>
                </div>
            </section>
        </main>
    );
}

export default AuthLayout;