/**
 * Settings Page
 * 
 * User settings with sections:
 * - Account: Email, password change
 * - Health Profile: Status, last updated, edit link
 * - Preferences: Notifications, language
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  User, 
  Heart, 
  Bell, 
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  LogOut,
  ArrowLeft,
  Edit2,
  Shield
} from 'lucide-react';
import { fetchProfileMe, ProfileMeResponse, fetchFullProfile, FullProfile } from '../services/profileApi';
import { logout } from '../utils/auth';
import './Settings.css';

// Debug mode - set to true to show saved profile data
const DEV_DEBUG_MODE = process.env.NODE_ENV === 'development';

export default function Settings() {
  const navigate = useNavigate();
  const [profileStatus, setProfileStatus] = useState<ProfileMeResponse | null>(null);
  const [fullProfile, setFullProfile] = useState<FullProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string>('');
  const [showDebug, setShowDebug] = useState(false);

  const loadProfile = useCallback(async () => {
    try {
      // Use the /me endpoint for status
      const status = await fetchProfileMe();
      setProfileStatus(status);
      
      // Also load full profile for debug display
      if (status.exists) {
        const full = await fetchFullProfile();
        setFullProfile(full);
      }
      
      // Debug logging
      if (DEV_DEBUG_MODE) {
        console.log('[Settings] Fetched profile status:', status);
      }
      
      // Get email from JWT token if available
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          setUserEmail(payload.sub || payload.email || '');
        } catch {
          // Invalid token format
        }
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleLogout = async () => {
    await logout();
    navigate('/', { replace: true });
  };

  const handleBack = () => {
    navigate(-1);
  };

  // Use is_completed from /me response (reflects DB truth)
  const isProfileComplete = profileStatus?.is_completed || false;
  const completionScore = profileStatus?.completion?.score || 0;
  const lastUpdated = profileStatus?.profile?.updated_at 
    ? new Date(profileStatus.profile.updated_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    : null;
  const completedAt = profileStatus?.profile?.completed_at
    ? new Date(profileStatus.profile.completed_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    : null;

  return (
    <div className="settings-page">
      <div className="settings-container">
        {/* Header */}
        <div className="settings-header">
          <button className="settings-back-btn" onClick={handleBack}>
            <ArrowLeft size={18} />
          </button>
          <h1>Settings</h1>
        </div>

        {/* Content */}
        <div className="settings-content">
          {/* Account Section */}
          <section className="settings-section">
            <h2 className="settings-section-title">
              <User size={18} />
              Account
            </h2>
            
            <div className="settings-card">
              <div className="settings-item">
                <div className="settings-item-info">
                  <span className="settings-item-label">Email</span>
                  <span className="settings-item-value">
                    {userEmail || 'Not available'}
                  </span>
                </div>
              </div>
              
              <div className="settings-divider" />
              
              <div className="settings-item settings-item-action">
                <div className="settings-item-info">
                  <span className="settings-item-label">Password</span>
                  <span className="settings-item-value">••••••••</span>
                </div>
                <button className="settings-item-btn">
                  Change
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </section>

          {/* Health Profile Section */}
          <section className="settings-section">
            <h2 className="settings-section-title">
              <Heart size={18} />
              Health Profile
            </h2>
            
            <div className="settings-card">
              <motion.div 
                className="settings-profile-status"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {loading ? (
                  <div className="settings-profile-loading">
                    <Loader2 className="animate-spin" size={20} />
                    <span>Loading profile...</span>
                  </div>
                ) : isProfileComplete ? (
                  <>
                    <div className="settings-profile-badge settings-profile-badge-complete">
                      <CheckCircle2 size={20} />
                      <span>Profile Complete ✅</span>
                    </div>
                    <div className="settings-profile-details">
                      <div className="settings-profile-stat">
                        <span className="stat-value">{completionScore.toFixed(0)}%</span>
                        <span className="stat-label">Completed</span>
                      </div>
                      {completedAt && (
                        <div className="settings-profile-stat">
                          <span className="stat-value">{completedAt}</span>
                          <span className="stat-label">Completed On</span>
                        </div>
                      )}
                      {lastUpdated && (
                        <div className="settings-profile-stat">
                          <span className="stat-value">{lastUpdated}</span>
                          <span className="stat-label">Last Updated</span>
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="settings-profile-badge settings-profile-badge-incomplete">
                      <AlertCircle size={20} />
                      <span>Profile Incomplete</span>
                    </div>
                    <p className="settings-profile-cta">
                      Complete your health profile for personalized recommendations
                    </p>
                  </>
                )}
              </motion.div>
              
              <button 
                className="settings-profile-btn"
                onClick={() => navigate('/health-profile')}
              >
                <Edit2 size={16} />
                {isProfileComplete ? 'Edit Profile' : 'Complete Profile'}
                <ChevronRight size={16} />
              </button>
              
              {/* Debug Section - Dev Only */}
              {DEV_DEBUG_MODE && (
                <div className="settings-debug">
                  <button 
                    className="settings-debug-toggle"
                    onClick={() => setShowDebug(!showDebug)}
                  >
                    {showDebug ? '▼' : '▶'} Debug Info (Dev Only)
                  </button>
                  
                  {showDebug && profileStatus && (
                    <div className="settings-debug-content">
                      <p className="debug-timestamp">
                        <strong>exists:</strong> {String(profileStatus.exists)}
                      </p>
                      <p className="debug-timestamp">
                        <strong>is_completed:</strong> {String(profileStatus.is_completed)}
                      </p>
                      <p className="debug-timestamp">
                        <strong>Last saved:</strong> {profileStatus.profile?.updated_at || 'Never'}
                      </p>
                      <p className="debug-timestamp">
                        <strong>Completed at:</strong> {profileStatus.profile?.completed_at || 'Never'}
                      </p>
                      <p className="debug-timestamp">
                        <strong>Wizard Step:</strong> {profileStatus.profile?.wizard_current_step || 1}
                      </p>
                      {fullProfile && (
                        <>
                          <p className="debug-timestamp">
                            <strong>Answers Count:</strong> {fullProfile.answers?.length || 0}
                          </p>
                          <p className="debug-timestamp">
                            <strong>Conditions Count:</strong> {fullProfile.conditions?.length || 0}
                          </p>
                        </>
                      )}
                      <details>
                        <summary>Raw Profile Data</summary>
                        <pre>{JSON.stringify(profileStatus.profile, null, 2)}</pre>
                      </details>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* Privacy Section */}
          <section className="settings-section">
            <h2 className="settings-section-title">
              <Shield size={18} />
              Privacy
            </h2>
            
            <div className="settings-card">
              <div className="settings-item settings-item-action">
                <div className="settings-item-info">
                  <span className="settings-item-label">Data & Privacy</span>
                  <span className="settings-item-value">Manage your data</span>
                </div>
                <button className="settings-item-btn">
                  View
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </section>

          {/* Notifications Section */}
          <section className="settings-section">
            <h2 className="settings-section-title">
              <Bell size={18} />
              Notifications
            </h2>
            
            <div className="settings-card">
              <div className="settings-item">
                <div className="settings-item-info">
                  <span className="settings-item-label">Email Notifications</span>
                  <span className="settings-item-value">Receive health insights by email</span>
                </div>
                <label className="settings-toggle">
                  <input type="checkbox" defaultChecked />
                  <span className="settings-toggle-slider"></span>
                </label>
              </div>
              
              <div className="settings-divider" />
              
              <div className="settings-item">
                <div className="settings-item-info">
                  <span className="settings-item-label">Report Reminders</span>
                  <span className="settings-item-value">Remind me to upload new reports</span>
                </div>
                <label className="settings-toggle">
                  <input type="checkbox" defaultChecked />
                  <span className="settings-toggle-slider"></span>
                </label>
              </div>
            </div>
          </section>

          {/* Logout */}
          <section className="settings-section">
            <button className="settings-logout-btn" onClick={handleLogout}>
              <LogOut size={18} />
              Log Out
            </button>
          </section>
        </div>
      </div>
    </div>
  );
}
