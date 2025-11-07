import { apiClient } from './api';
import type { User } from '../types';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  token?: string;
  isAuthenticated?: boolean;
}

export interface MSALLoginResponse {
  auth_url: string;
  message: string;
}

export interface MSALCallbackResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface TokenValidationResponse {
  valid: boolean;
  payload?: {
    user_id: string;
    email: string;
    expires: number;
  };
  error?: string;
}

export const authService = {
  // ========== MSAL + JWT Authentication ==========

  // Step 1: Initiate MSAL login flow
  initiateMSALLogin: () =>
    apiClient.post<MSALLoginResponse>('/api/auth/login'),

  // Step 2: Handle MSAL callback and get JWT tokens
  // Note: This will be called by the callback URL with query parameters
  handleMSALCallback: (queryParams: string) =>
    apiClient.get<MSALCallbackResponse>(`/api/auth/callback${queryParams}`),

  // Refresh access token using refresh token
  refreshToken: (refreshToken: string) =>
    apiClient.post<RefreshTokenResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
    }),

  // Get current session/user (requires valid JWT in header)
  getCurrentSession: () =>
    apiClient.get<AuthResponse>('/api/auth/session'),

  // Logout current user
  logout: () =>
    apiClient.post<{ message: string; logout_url: string }>('/api/auth/logout'),

  // Validate JWT token
  validateToken: (token: string) =>
    apiClient.post<TokenValidationResponse>('/api/auth/validate', { token }),

  // ========== Token Management ==========

  // Store tokens in localStorage
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },

  // Get access token from localStorage
  getAccessToken: (): string | null => {
    return localStorage.getItem('access_token');
  },

  // Get refresh token from localStorage
  getRefreshToken: (): string | null => {
    return localStorage.getItem('refresh_token');
  },

  // Clear tokens from localStorage
  clearTokens: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  // Check if user has valid token
  // For session-based auth (dev mode), we always return true and let the session endpoint decide
  hasValidToken: (): boolean => {
    const token = authService.getAccessToken();
    // Always return true to allow session-based auth to work
    // The actual auth check happens in getCurrentSession()
    return true;
  },
};
