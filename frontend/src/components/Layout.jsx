import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { path: '/', label: 'Home', icon: '🏠' },
  { path: '/policy', label: 'Policy', icon: '📋' },
  { path: '/claims', label: 'Claims', icon: '💰' },
  { path: '/profile', label: 'Profile', icon: '👤' },
  { path: '/admin', label: 'Admin', icon: '⚙️' },
];

export function Layout({ children }) {
  const location = useLocation();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col safe-top safe-bottom">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">🛡️</span>
            <span className="font-bold text-lg text-gray-900">RapidCover</span>
          </Link>
          {user && (
            <span className="text-sm text-gray-600">
              {user.name}
            </span>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-4 py-6 max-w-lg mx-auto w-full">
        {children}
      </main>

      {/* Bottom Navigation */}
      {user && (
        <nav className="bg-white border-t border-gray-200 px-4 py-2">
          <div className="max-w-lg mx-auto flex justify-around">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex flex-col items-center py-2 px-3 rounded-lg transition-colors ${isActive
                      ? 'text-blue-600'
                      : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                  <span className="text-xl">{item.icon}</span>
                  <span className="text-xs mt-1">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </div>
  );
}
