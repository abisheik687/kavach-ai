
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import MainLayout from './layout/MainLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import ScanPage from './pages/ScanPage';
import AlertsPage from './pages/AlertsPage';
import ResultsPage from './pages/ResultsPage';
import LiveStreamPage from './pages/LiveStreamPage';

const ProtectedRoute = ({ children }) => {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="scan" element={<ScanPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="alerts/:alertId" element={<ResultsPage />} />
            <Route path="live" element={<LiveStreamPage />} />
            {/* Catch-all explicitly wrapped so it sits inside layout */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
