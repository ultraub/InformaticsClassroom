import { apiClient } from './api';
import type { User } from '../types';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  token?: string;
}

export const authService = {
  // Login with username and password
  login: (credentials: LoginCredentials) =>
    apiClient.post<AuthResponse>('/api/auth/login', credentials),

  // Logout current user
  logout: () =>
    apiClient.post<void>('/api/auth/logout'),

  // Get current session/user
  getCurrentSession: () =>
    apiClient.get<AuthResponse>('/api/auth/session'),

  // Refresh authentication token
  refreshToken: () =>
    apiClient.post<AuthResponse>('/api/auth/refresh'),

  // Check if user is authenticated
  isAuthenticated: () =>
    apiClient.get<{ authenticated: boolean }>('/api/auth/check'),
};
