import { apiClient } from './api';
import type { ApiResponse } from '../types';

export interface ClassMember {
  user_id: string;
  email: string;
  display_name: string;
  role: 'instructor' | 'ta' | 'student';
  assigned_at?: string;
  assigned_by?: string;
}

export interface ClassMembersResponse {
  success: boolean;
  class_id: string;
  members: ClassMember[];
  count: number;
  error?: string;
}

export interface AddMemberRequest {
  user_id: string;
  role: 'instructor' | 'ta' | 'student';
}

export interface UpdateMemberRequest {
  role: 'instructor' | 'ta' | 'student';
}

export interface MemberActionResponse {
  success: boolean;
  message?: string;
  user_id?: string;
  class_id?: string;
  role?: string;
  error?: string;
}

export const classesService = {
  // Get all members of a class
  getClassMembers: (classId: string) =>
    apiClient.get<ClassMembersResponse>(`/api/classes/${classId}/members`),

  // Add a member to a class
  addClassMember: (classId: string, data: AddMemberRequest) =>
    apiClient.post<MemberActionResponse>(`/api/classes/${classId}/members`, data),

  // Update a member's role in a class
  updateClassMember: (classId: string, userId: string, data: UpdateMemberRequest) =>
    apiClient.put<MemberActionResponse>(`/api/classes/${classId}/members/${userId}`, data),

  // Remove a member from a class
  removeClassMember: (classId: string, userId: string) =>
    apiClient.delete<MemberActionResponse>(`/api/classes/${classId}/members/${userId}`),
};
