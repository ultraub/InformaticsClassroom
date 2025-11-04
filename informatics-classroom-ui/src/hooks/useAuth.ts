import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';
import { authService, type LoginCredentials } from '../services/auth';
import { usersService } from '../services/users';

export function useAuth() {
  const { user, isAuthenticated, setUser, setLoading, login, logout: storeLogout } = useAuthStore();
  const queryClient = useQueryClient();

  // Check current session on mount
  const { data: sessionData, isLoading: sessionLoading } = useQuery({
    queryKey: ['auth', 'session'],
    queryFn: async () => {
      const response = await authService.getCurrentSession();
      return response.data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Update auth store when session data changes
  useEffect(() => {
    if (sessionData?.user) {
      setUser(sessionData.user);
    }
    setLoading(false);
  }, [sessionData, setUser, setLoading]);

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await authService.login(credentials);
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Login failed');
      }
      return response.data;
    },
    onSuccess: (data) => {
      login(data.user);
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: async () => {
      const response = await authService.logout();
      if (!response.success) {
        throw new Error(response.error || 'Logout failed');
      }
    },
    onSuccess: () => {
      storeLogout();
      queryClient.clear();
      window.location.href = '/login';
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
  };
}
