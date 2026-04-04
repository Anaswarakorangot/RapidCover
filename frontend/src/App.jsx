import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext.jsx';
import { Layout } from './components/Layout';
import { Login, Register, Dashboard, Policy, Claims, Profile, Admin } from './pages';
import RapidCoverOnboarding from './components/ui/RapidCoverOnboarding.jsx';
import OnboardingFlow from './components/ui/OnboardingFlow';

// Loader UI
const Loader = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
  </div>
);

// Protected Route
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <Loader />;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Layout>{children}</Layout>;
}

// Public Route
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <Loader />;

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

// Onboarding Screen
function OnboardingRoute() {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  if (loading) return <Loader />;

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <OnboardingFlow 
      onFinish={() => navigate('/register')} 
      onLogin={() => navigate('/login')}
    />
  );
}

// Admin Route — full-screen dark panel, no Layout wrapper
function AdminRoute() {
  const { loading } = useAuth();
  if (loading) return <Loader />;
  return <Admin />;
}

// Root Route
function RootRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <Loader />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <Navigate to="/onboarding" replace />;
}

// Routes
function AppRoutes() {
  return (
    <Routes>
      <Route path="/onboarding" element={<OnboardingRoute />} />

      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

      <Route path="/" element={<RootRoute />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/policy" element={<ProtectedRoute><Policy /></ProtectedRoute>} />
      <Route path="/claims" element={<ProtectedRoute><Claims /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
      <Route path="/admin" element={<AdminRoute />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// Online status hook
function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  return isOnline;
}

// App
export default function App() {
  const isOnline = useOnlineStatus();
  
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          {!isOnline && (
            <div style={{
              background: '#1a2e1a', color: '#fff', fontSize: 12, padding: '8px 16px',
              textAlign: 'center', fontWeight: 600, position: 'sticky', top: 0, zIndex: 10000,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8
            }}>
              Offline Mode - Syncing locally to RapidCover Edge
            </div>
          )}
          <AppRoutes />
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}