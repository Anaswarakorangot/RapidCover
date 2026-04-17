/**
 * AdminAuthContext.jsx
 *
 * Manages admin session state separately from partner authentication.
 * Exposes: admin, login, logout, loading
 * On mount, reads admin_token from localStorage and restores session.
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { loginAdmin, getAdminProfile } from '../services/adminApi';

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoading(false);
      return;
    }

    // Try to restore session with stored token
    getAdminProfile()
      .then(profile => {
        setAdmin(profile);
      })
      .catch(() => {
        // Token invalid or expired
        localStorage.removeItem('admin_token');
        setAdmin(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  async function login(email, password) {
    const response = await loginAdmin(email, password);
    localStorage.setItem('admin_token', response.access_token);
    setAdmin(response.admin);
    return response;
  }

  function logout() {
    localStorage.removeItem('admin_token');
    setAdmin(null);
  }

  const value = {
    admin,
    login,
    logout,
    loading,
    isAuthenticated: !!admin,
  };

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  );
}

/* eslint-disable react-refresh/only-export-components */
export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within AdminAuthProvider');
  }
  return context;
}
