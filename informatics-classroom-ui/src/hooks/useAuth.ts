import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';
import { authService } from '../services/auth';
import { usersService } from '../services/users';

export function useAuth() {
  const { user, isAuthenticated, setUser, setLoading, login, logout: storeLogout } = useAuthStore();
  const queryClient = useQueryClient();
  const [callbackError, setCallbackError] = useState<string | null>(null);

  // Handle MSAL callback on mount if we're on the callback route
  useEffect(() => {
    const handleMSALCallback = async () => {
      // Check if we're on the callback route with query parameters
      const queryParams = window.location.search;
      if (queryParams.includes('code=') || queryParams.includes('error=')) {
        setLoading(true);
        try {
          const response = await authService.handleMSALCallback(queryParams);
          if (response.success && response.data) {
            // Store JWT tokens
            authService.setTokens(
              response.data.access_token,
              response.data.refresh_token
            );
            // Update auth store with user data
            login(response.data.user);
            // Clear query parameters and redirect to home
            window.history.replaceState({}, document.title, '/');
          } else {
            setCallbackError(response.error || 'Authentication failed');
            authService.clearTokens();
          }
        } catch (error) {
          console.error('MSAL callback error:', error);
          setCallbackError(error instanceof Error ? error.message : 'Authentication failed');
          authService.clearTokens();
        } finally {
          setLoading(false);
        }
      }
    };

    handleMSALCallback();
  }, [setLoading, login]);

  // Check for existing JWT token and validate session on mount
  const { data: sessionData, isLoading: sessionLoading } = useQuery({
    queryKey: ['auth', 'session'],
    queryFn: async () => {
      // Check session - works for both JWT tokens and session cookies
      const response = await authService.getCurrentSession();
      // If the request succeeded, return the data
      if (response.success && response.data) {
        return response.data;
      }
      // If it failed, return null so we know there's no session
      return null;
    },
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: true, // Always try to check session (handles both JWT and session-based auth)
  });

  // Update auth store when session data changes
  useEffect(() => {
    // Don't update auth state while query is still loading
    if (sessionLoading) {
      return;
    }

    if (sessionData?.user) {
      setUser(sessionData.user);
    } else {
      // No session, ensure we're logged out
      storeLogout();
    }
    setLoading(false);
  }, [sessionData, sessionLoading, setUser, setLoading, storeLogout]);

  // Initiate MSAL login mutation
  const loginMutation = useMutation({
    mutationFn: async () => {
      const response = await authService.initiateMSALLogin();
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to initiate login');
      }
      return response.data;
    },
    onSuccess: (data) => {
      // Redirect user to MSAL auth URL
      window.location.href = data.auth_url;
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: async () => {
      const response = await authService.logout();
      if (!response.success) {
        throw new Error(response.error || 'Logout failed');
      }
      return response.data;
    },
    onSuccess: (data) => {
      // Clear tokens and auth state
      authService.clearTokens();
      storeLogout();
      queryClient.clear();
      // Redirect to Microsoft logout if available
      if (data?.logout_url) {
        window.location.href = data.logout_url;
      } else {
        window.location.href = '/login';
      }
    },
  });

  // Get current user with permissions
  const { data: currentUserData } = useQuery({
    queryKey: ['user', 'me'],
    queryFn: async () => {
      const response = await usersService.getCurrentUser();
      return response.data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  return {
    user: currentUserData || user,
    isAuthenticated,
    isLoading: sessionLoading || loginMutation.isPending || logoutMutation.isPending,
    login: loginMutation.mutate,
    logout: logoutMutation.mutate,
    loginError: loginMutation.error as Error | null,
    logoutError: logoutMutation.error as Error | null,
    callbackError,
  };
}
