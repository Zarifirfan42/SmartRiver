import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/common/ProtectedRoute'
import AppLayout from './components/layout/AppLayout'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import Dashboard from './pages/Dashboard'
import RiverHealthPage from './pages/RiverHealthPage'
import PollutionForecastPage from './pages/PollutionForecastPage'
import AlertMonitoringPage from './pages/AlertMonitoringPage'
import AnomalyDetectionPage from './pages/AnomalyDetectionPage'
import ReportExportPage from './pages/ReportExportPage'
import DatasetUploadPage from './pages/DatasetUploadPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
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
            <Route path="anomaly-detection" element={<AnomalyDetectionPage />} />
            <Route path="export" element={<ReportExportPage />} />
            <Route
              path="upload"
              element={
                <ProtectedRoute requireAdmin>
                  <DatasetUploadPage />
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
