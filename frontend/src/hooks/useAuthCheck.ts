import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import apiClient from '@/lib/apiClient';
import { setUser, logout, setLoading } from '@/redux/slices/authReducer';

export const useAuthCheck = () => {
  const dispatch = useDispatch();

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      // Indicate loading
      dispatch(setLoading(true));
      try {
        // Call protected endpoint; axios interceptor will try refresh on 401 once.
        const resp = await apiClient.get('/auth/user/');
        if (!mounted) return;
        dispatch(setUser(resp.data));
      } catch (error: any) {
        // If final outcome is 401 -> logout. Any other error -> do not logout automatically.
        if (error?.response?.status === 401) {
          // Final unauthenticated after refresh attempt — trigger logout.
          dispatch(logout());
        } else {
          // Non-auth related error: keep user state untouched; set loading false.
          dispatch(setLoading(false));
        }
      } finally {
        if (mounted) dispatch(setLoading(false));
      }
    };
    check();
    return () => {
      mounted = false;
    };
  }, [dispatch]);
};