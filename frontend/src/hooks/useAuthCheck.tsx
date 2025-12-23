// /src/hooks/useAuthCheck.ts (DEBUGGING & ROBUSTNESS UPDATE)

import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import Cookies from 'js-cookie';
import { setLoading, setUser, logout } from './../redux/slices/authReducer';
import apiClient from './../lib/apiClient'; 

export const useAuthCheck = () => {
    const dispatch = useDispatch();

    useEffect(() => {
        const checkAuthStatus = async () => {
            const accessToken = Cookies.get('access_token');
            const refreshToken = Cookies.get('refresh_token');

            if (!accessToken && !refreshToken) {
                console.log("AUTH CHECK: No tokens found. User is logged out.");
                dispatch(logout()); // Ensure state is reset
                dispatch(setLoading(false));
                return;
            }

            console.log("AUTH CHECK: Token(s) found. Attempting session verification...");
            
            // 1. Attempt to call a protected endpoint
            try {
                // If the accessToken is valid, we get user data.
                // If it's expired, the Interceptor will attempt to refresh it and retry this call.
                const response = await apiClient.get('/auth/user/'); 
                
                // Success: Token was valid or successfully renewed and retried.
                dispatch(setUser(response.data));
                console.log("AUTH CHECK: Success! User session verified and set.");
                
            } catch (error: any) {
                console.error("AUTH CHECK: Verification failed after refresh attempt.", error.response?.status, error.message);
                
                // If the interceptor failed to renew the token, the error status will be caught here.
                // The interceptor's job is to clear cookies, but we finalize Redux state here.
                if (error.response?.status === 401) {
                    // This 401 means the refresh token failed, or the initial token was bad.
                    dispatch(logout());
                    console.log("AUTH CHECK: Final 401 received. User logged out.");
                } else {
                    // Handle network errors or other non-auth errors gracefully
                    console.error("AUTH CHECK: Non-401 error. Assuming session is invalid.");
                    dispatch(logout());
                }
            } finally {
                // 2. Crucial Step: ALWAYS end the loading state.
                dispatch(setLoading(false));
                console.log("AUTH CHECK: Loading state finalized.");
            }
        };

        checkAuthStatus();
        
    }, [dispatch]);
};