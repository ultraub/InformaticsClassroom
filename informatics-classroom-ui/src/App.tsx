import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Layout } from './components/layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Users } from './pages/Users';
import { AuditLogs } from './pages/AuditLogs';
import StudentCenter from './pages/StudentCenter';
import QuizTaking from './pages/QuizTaking';
import QuizBuilder from './pages/QuizBuilder';
import TokenGenerator from './pages/TokenGenerator';
import AssignmentAnalysis from './pages/AssignmentAnalysis';
import ExerciseReview from './pages/ExerciseReview';
import ClassManagement from './pages/ClassManagement';
import ClassSelector from './pages/ClassSelector';
import { SubmitAnswers } from './pages/SubmitAnswers';
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

          {/* Class Selector */}
          <Route
            path="/classes"
            element={
              <ProtectedRoute requiredRole={Role.TA}>
                <Layout>
                  <ClassSelector />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Class Management - Unified Interface */}
          <Route
            path="/classes/:classId/manage"
            element={
              <ProtectedRoute requiredRole={Role.TA}>
                <Layout>
                  <ClassManagement />
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

          {/* Student Center */}
          <Route
            path="/student"
            element={
              <ProtectedRoute>
                <Layout>
                  <StudentCenter />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Quiz Taking */}
          <Route
            path="/quiz"
            element={
              <ProtectedRoute>
                <Layout>
                  <QuizTaking />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Submit Answers */}
          <Route
            path="/submit-answers"
            element={
              <ProtectedRoute>
                <Layout>
                  <SubmitAnswers />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Quiz Builder - Create */}
          <Route
            path="/quiz/create"
            element={
              <ProtectedRoute requiredRole={Role.TA}>
                <Layout>
                  <QuizBuilder />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Quiz Builder - Edit */}
          <Route
            path="/quiz/edit"
            element={
              <ProtectedRoute requiredRole={Role.TA}>
                <Layout>
                  <QuizBuilder />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Token Generator */}
          <Route
            path="/tokens/generate"
            element={
              <ProtectedRoute requiredRole={Role.TA}>
                <Layout>
                  <TokenGenerator />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Assignment Analysis */}
          <Route
            path="/assignments/analyze"
            element={
              <ProtectedRoute requiredRole={Role.TA}>
                <Layout>
                  <AssignmentAnalysis />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Exercise Review */}
          <Route
            path="/exercises/review"
            element={
              <ProtectedRoute>
                <Layout>
                  <ExerciseReview />
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
