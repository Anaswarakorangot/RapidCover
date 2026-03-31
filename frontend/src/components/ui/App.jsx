import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import RapidCoverOnboarding from './components/ui/RapidCoverOnboarding';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Claims from './pages/Claims';
import Policy from './pages/Policy';
import Profile from './pages/Profile';
import Admin from './pages/Admin';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Onboarding is the first screen */}
        <Route path="/" element={<RapidCoverOnboarding onGetStarted={() => window.location.href = '/login'} />} />
        
        {/* Rest of your pages */}
        <Route path="/login"     element={<Login />} />
        <Route path="/register"  element={<Register />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/claims"    element={<Claims />} />
        <Route path="/policy"    element={<Policy />} />
        <Route path="/profile"   element={<Profile />} />
        <Route path="/admin"     element={<Admin />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;