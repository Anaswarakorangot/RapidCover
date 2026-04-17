import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { path: '/', label: 'Home', icon: '🏠' },
  { path: '/policy', label: 'Policy', icon: '📋' },
  { path: '/claims', label: 'Claims', icon: '💰' },
  { path: '/trust-center', label: 'Trust', icon: '🔍' },
  { path: '/profile', label: 'Profile', icon: '👤' },
  { path: '/admin', label: 'Admin', icon: '⚙️' },
];

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&display=swap');

  .rc-header {
    background: linear-gradient(135deg, #3DB85C 0%, #2a9e47 100%);
    padding: 14px 16px;
    box-shadow: 0 2px 8px rgba(61, 184, 92, 0.15);
  }
  .rc-header__inner {
    max-width: 480px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .rc-header__brand {
    display: flex;
    align-items: center;
    gap: 8px;
    text-decoration: none;
  }
  .rc-header__logo {
    width: 36px;
    height: 36px;
    background: rgba(255,255,255,0.2);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
  }
  .rc-header__title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 20px;
    color: white;
    letter-spacing: -0.3px;
  }
  .rc-header__user {
    font-size: 13px;
    color: rgba(255,255,255,0.9);
    font-weight: 600;
    background: rgba(255,255,255,0.15);
    padding: 6px 12px;
    border-radius: 20px;
  }

  .rc-nav {
    background: white;
    border-top: 1px solid #e2ece2;
    padding: 8px 12px 12px;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    position: sticky;
    bottom: 0;
    z-index: 1000;
  }
  .rc-nav__inner {
    max-width: 480px;
    margin: 0 auto;
    display: flex;
    justify-content: space-around;
  }
  .rc-nav__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 12px;
    border-radius: 12px;
    text-decoration: none;
    transition: all 0.2s ease;
    min-width: 56px;
  }
  .rc-nav__item--active {
    background: #e8f7ed;
  }
  .rc-nav__icon {
    font-size: 22px;
    margin-bottom: 4px;
  }
  .rc-nav__label {
    font-size: 11px;
    font-weight: 700;
    color: #8a9e8a;
  }
  .rc-nav__item--active .rc-nav__label {
    color: #3DB85C;
  }

  .rc-main {
    flex: 1;
    padding: 20px 16px;
    max-width: 480px;
    margin: 0 auto;
    width: 100%;
    background: #f7f9f7;
  }
`;

export function Layout({ children }) {
  const location = useLocation();
  const { user } = useAuth();

  return (
    <>
      <style>{styles}</style>
      <div className="min-h-screen bg-gray-50 flex flex-col safe-top safe-bottom">
        {/* Header */}
        <header className="rc-header">
          <div className="rc-header__inner">
            <Link to="/" className="rc-header__brand">
              <div className="rc-header__logo">🛡️</div>
              <span className="rc-header__title">RapidCover</span>
            </Link>
            {user && (
              <span className="rc-header__user">
                {user.name}
              </span>
            )}
          </div>
        </header>

        {/* Main Content */}
        <main className="rc-main">
          {children}
        </main>

        {/* Bottom Navigation */}
        {user && (
          <nav className="rc-nav">
            <div className="rc-nav__inner">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`rc-nav__item ${isActive ? 'rc-nav__item--active' : ''}`}
                  >
                    <span className="rc-nav__icon">{item.icon}</span>
                    <span className="rc-nav__label">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </nav>
        )}
      </div>
    </>
  );
}
