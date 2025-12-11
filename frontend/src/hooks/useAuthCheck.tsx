// /src/hooks/useAuthCheck.ts (FINAL IMPLEMENTATION)

import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import Cookies from 'js-cookie';
import { setLoading, setUser, logout } from '@/redux/slices/authReducer'; // Import logout
import apiClient from '@/lib/apiClient'; // Import the client with interceptors

export const useAuthCheck = () => {
    const dispatch = useDispatch();

    useEffect(() => {
        const checkAuthStatus = async () => {
            const accessToken = Cookies.get('access_token');

            // 1. Quick check: If no access token, we are logged out (end loading)
            if (!accessToken) {
                dispatch(logout());
                dispatch(setLoading(false));
                return;
            }
            
            // 2. Secure API Call to verify token validity and fetch user details
            try {
                // This request is protected. If the token is expired, the interceptor 
                // will automatically try to refresh it and retry this call.
                const response = await apiClient.get('/auth/user/');
                
                // If successful (token was valid or successfully refreshed):
                dispatch(setUser(response.data));
            } catch (error) {
                // If the interceptor fails to refresh the token (refresh token expired),
                // the final error is caught here. We ensure the user is logged out.
                dispatch(logout());
            } finally {
                // 3. Crucial step: End the loading state unconditionally
                dispatch(setLoading(false));
            }
        };

        checkAuthStatus();
        
    }, [dispatch]); // Run only on mount
};