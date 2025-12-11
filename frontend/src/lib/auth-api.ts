// The central service layer for authentication requests, token management, and state updates.

import Cookies from 'js-cookie';
import { Dispatch } from '@reduxjs/toolkit';
import { setUser, logout, setError } from '@/redux/slices/authReducer';
import apiClient from './apiClient'; 

// Base path for authentication endpoints defined in Django
const API_AUTH_URL = '/auth'; 

// --- 1. HANDLE LOGIN ---
export const handleLogin = async (credentials: any, dispatch: Dispatch<any>, router: any) => {
  try {
    // Calls /api/v1/auth/login/
    const response = await apiClient.post(`${API_AUTH_URL}/login/`, credentials);
    
    // We expect access, refresh tokens, and user details in the response
    const { access, refresh, user } = response.data; 

    // Store tokens securely in cookies (recommended settings for security)
    Cookies.set('access_token', access, { expires: 1/24, secure: true, sameSite: 'Lax' }); // 1 hour
    Cookies.set('refresh_token', refresh, { expires: 7, secure: true, sameSite: 'Lax' }); // 7 days

    // Update Redux state
    dispatch(setUser(user));

    // Redirect to the home page on success
    router.push('/home');
    return true;

  } catch (error: any) {
    // Extract a user-friendly error message
    const errorMessage = error.response?.data?.detail 
                        || error.response?.data?.non_field_errors?.[0] 
                        || 'Login failed. Please check your credentials.';
                        
    dispatch(setError(errorMessage));
    console.error("Login API Error:", error);
    return false;
  }
};

// --- 2. HANDLE REGISTER ---
export const handleRegister = async (data: any, dispatch: Dispatch<any>, router: any) => {
  try {
    // Calls /api/v1/auth/register/
    // Since the backend is configured for auto-login, we expect tokens in the response.
    const response = await apiClient.post(`${API_AUTH_URL}/register/`, data);
    
    // We expect the auto-login response containing tokens and user data
    const { access, refresh, user } = response.data;

    // Store tokens securely in cookies
    Cookies.set('access_token', access, { expires: 1/24, secure: true, sameSite: 'Lax' }); 
    Cookies.set('refresh_token', refresh, { expires: 7, secure: true, sameSite: 'Lax' });

    // Update Redux state
    dispatch(setUser(user));
    
    // Redirect to the home page on success
    router.push('/home');
    return true;

  } catch (error: any) {
    // Handle specific validation errors from the Django serializer
    const errorData = error.response?.data;
    let errorMessage = 'Registration failed due to an unknown error.';
    
    if (errorData?.email) {
      errorMessage = `Email: ${errorData.email[0]}`;
    } else if (errorData?.username) {
      errorMessage = `Username: ${errorData.username[0]}`;
    } else if (errorData?.password) {
      errorMessage = `Password: ${errorData.password[0]}`;
    } else if (errorData?.non_field_errors) {
        errorMessage = errorData.non_field_errors[0];
    }
    
    dispatch(setError(errorMessage));
    console.error("Registration API Error:", error);
    return false;
  }
};

// --- 3. HANDLE LOGOUT ---
export const handleLogout = (dispatch: Dispatch<any>, router: any) => {
    // 1. Clear tokens from browser cookies
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
    
    // 2. Clear user state from Redux
    dispatch(logout());
    
    // 3. Redirect to the login page (which is handled by the root page redirector)
    router.push('/login');
};

// Exporting the client setup for direct use in hooks/components if needed
export default apiClient;