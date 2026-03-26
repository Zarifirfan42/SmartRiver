import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/common/ProtectedRoute'
import AppLayout from './components/layout/AppLayout'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import Dashboard from './pages/Dashboard'
import RiverHealthPage from './pages/RiverHealthPage'
import PollutionForecastPage from './pages/PollutionForecastPage'
import AlertMonitoringPage from './pages/AlertMonitoringPage'
import AnomalyDetectionPage from './pages/AnomalyDetectionPage'
import DatasetUploadPage from './pages/DatasetUploadPage'
import FeedbackReportsPage from './pages/FeedbackReportsPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="river-health" element={<RiverHealthPage />} />
            <Route path="forecast" element={<PollutionForecastPage />} />
            <Route path="alerts" element={<AlertMonitoringPage />} />
            <Route
              path="anomaly-detection"
              element={
                <ProtectedRoute requireAdmin>
                  <AnomalyDetectionPage />
                </ProtectedRoute>
              }
            />
            <Route path="export" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="upload"
              element={
                <ProtectedRoute requireAdmin>
                  <DatasetUploadPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="feedback-reports"
              element={
                <ProtectedRoute requireAdmin>
                  <FeedbackReportsPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
