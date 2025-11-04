import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Layout } from './components/layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Users } from './pages/Users';
import { PermissionMatrix } from './pages/PermissionMatrix';
import { RoleTemplates } from './pages/RoleTemplates';
import { AuditLogs } from './pages/AuditLogs';
import { Role } from './types';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout>
                  <Dashboard />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* User Management */}
          <Route
            path="/users"
            element={
              <ProtectedRoute>
                <Layout>
                  <Users />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Permission Matrix */}
          <Route
            path="/permissions"
            element={
              <ProtectedRoute>
                <Layout>
                  <PermissionMatrix />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Role Templates */}
          <Route
            path="/templates"
            element={
              <ProtectedRoute>
                <Layout>
                  <RoleTemplates />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Audit Logs */}
          <Route
            path="/audit"
            element={
              <ProtectedRoute requiredRole={Role.ADMIN}>
                <Layout>
                  <AuditLogs />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Quizzes */}
          <Route
            path="/quizzes"
            element={
              <ProtectedRoute>
                <Layout>
                  <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-900">Quizzes</h2>
                    <p className="text-gray-600 mt-2">Quiz management coming soon...</p>
                  </div>
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Assignments */}
          <Route
            path="/assignments"
            element={
              <ProtectedRoute>
                <Layout>
                  <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-900">Assignments</h2>
                    <p className="text-gray-600 mt-2">Assignment management coming soon...</p>
                  </div>
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Profile and Settings */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Layout>
                  <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-900">Your Profile</h2>
                    <p className="text-gray-600 mt-2">Profile page coming soon...</p>
                  </div>
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Layout>
                  <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
                    <p className="text-gray-600 mt-2">Settings page coming soon...</p>
                  </div>
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Catch all - redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
