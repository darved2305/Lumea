import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings, LogOut, Home, LayoutDashboard, Bell, FileText, Activity, Sparkles, Pill, PhoneCall } from 'lucide-react';
import { logout } from '../../utils/auth';
import Logo from '../ui/Logo';
import './DashboardNavbar.css';

interface DashboardNavbarProps {
  userName?: string;
  userStatus?: string;
}

function DashboardNavbar({ userName = 'User', userStatus = '87% Healthy' }: DashboardNavbarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const navItems = [
    { label: 'Home', path: '/', icon: Home },
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Reports', path: '/reports', icon: FileText },
    { label: 'Voice Agent', path: '/voice-agent', icon: PhoneCall },
    { label: 'Physics Twin', path: '/physics-twin', icon: Activity },
    { label: 'AI Summary', path: '/report-summary', icon: Sparkles },
    { label: 'Recommendations', path: '/recommendations', icon: Activity },
    { label: 'Medicines', path: '/medicines', icon: Pill },
  ];

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    setIsUserMenuOpen(false);
    await logout();
    navigate('/', { replace: true });
  };

  return (
    <motion.nav
      className="dashboard-navbar"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <div className="dashboard-navbar-container">
        {/* Logo */}
        <Link to="/" className="dashboard-logo">
          <Logo variant="dashboard" />
        </Link>

        {/* Navigation Links */}
        <div className="dashboard-nav">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`dashboard-nav-link ${isActive(item.path) ? 'active' : ''}`}
            >
              <motion.span
                whileHover={{ scale: 1.05 }}
                transition={{ type: 'spring', stiffness: 400 }}
              >
                {item.label}
              </motion.span>
            </Link>
          ))}
        </div>

        {/* Actions */}
        <div className="dashboard-actions">
          {/* Notifications */}
          <motion.button
            className="dash-btn dash-btn-icon dash-focus-ring"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            aria-label="Notifications"
          >
            <Bell size={20} />
          </motion.button>

          {/* User Menu */}
          <div className="dashboard-user-menu">
            <motion.button
              className="dashboard-user-button dash-focus-ring"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="dashboard-user-avatar">
                {userName.charAt(0).toUpperCase()}
              </div>
              <div className="dashboard-user-info">
                <span className="dashboard-user-name">{userName}</span>
                <span className="dashboard-user-status">{userStatus}</span>
              </div>
            </motion.button>

            {/* Dropdown */}
            <AnimatePresence>
              {isUserMenuOpen && (
                <motion.div
                  className="dashboard-user-dropdown open"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <Link
                    to="/dashboard"
                    className="dashboard-user-dropdown-item"
                    onClick={() => setIsUserMenuOpen(false)}
                  >
                    <LayoutDashboard size={16} />
                    Dashboard
                  </Link>
                  <Link
                    to="/settings"
                    className="dashboard-user-dropdown-item"
                    onClick={() => setIsUserMenuOpen(false)}
                  >
                    <Settings size={16} />
                    Settings
                  </Link>
                  <div className="dashboard-user-dropdown-divider" />
                  <button
                    className="dashboard-user-dropdown-item"
                    onClick={handleLogout}
                  >
                    <LogOut size={16} />
                    Logout
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </motion.nav>
  );
}

export default DashboardNavbar;
