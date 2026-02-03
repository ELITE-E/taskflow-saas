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
      dispatch(setLoading(true));
      try {
        const resp = await apiClient.get('/auth/user/');
        dispatch(setUser(resp.data));
      } catch (error: any) {
        if (error?.response?.status === 401) {
          dispatch(logout());
        }
      } finally {
        dispatch(setLoading(false));
      }
    };

    checkAuthStatus();
  }, [dispatch]);
};