/**
 * Health Profile Card Component
 * 
 * Shows profile status using the /api/profile/me endpoint:
 * - First-time user (exists=false or is_completed=false): "Complete your health profile" CTA
 * - In-progress: Resume wizard prompt
 * - Completed (is_completed=true): Success state with "Edit Profile" button -> Settings
 * 
 * Once profile is completed, user is NEVER asked to fill again.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Edit2, 
  CheckCircle2, 
  ChevronRight,
  Activity,
  Heart,
  Loader2,
  Settings
} from 'lucide-react';
import { fetchProfileMe, ProfileMeResponse, fetchFullProfile, FullProfile } from '../../services/profileApi';
import './HealthProfileCard.css';

interface HealthProfileCardProps {
  onProfileUpdated?: () => void;
}

export default function HealthProfileCard({ onProfileUpdated: _onProfileUpdated }: HealthProfileCardProps) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [profileStatus, setProfileStatus] = useState<ProfileMeResponse | null>(null);
  const [fullProfile, setFullProfile] = useState<FullProfile | null>(null);
  
  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      // Use the simpler /me endpoint for status check
      const status = await fetchProfileMe();
      setProfileStatus(status);
      
      // If profile exists and is complete, also fetch full profile for display
      if (status.exists && status.is_completed) {
        const full = await fetchFullProfile();
        setFullProfile(full);
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
  
  const handleGetStarted = () => {
    navigate('/health-profile');
  };
  
  const handleEditProfile = () => {
    // Navigate to Settings page for editing completed profile
    navigate('/settings');
  };
  
  // Determine profile state from /me response
  const exists = profileStatus?.exists || false;
  const isCompleted = profileStatus?.is_completed || false;
  const completionScore = profileStatus?.completion?.score || 0;
  
  // Check if in progress (has profile but not completed, and has made some progress)
  const wizardStep = profileStatus?.profile?.wizard_current_step || 1;
  const inProgress = exists && !isCompleted && wizardStep > 1;
  
  // Loading state
  if (loading) {
    return (
      <div className="profile-card profile-card-loading">
        <Loader2 className="animate-spin" size={24} />
        <span>Loading profile...</span>
      </div>
    );
  }
  
  // COMPLETED - Show success state with Edit button (routes to Settings)
  if (isCompleted) {
    const profile = fullProfile?.profile || profileStatus?.profile;
    
    return (
      <motion.div 
        className="profile-card profile-card-complete"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="profile-card-header">
          <div className="profile-card-icon profile-card-icon-success">
            <CheckCircle2 size={24} />
          </div>
          <div>
            <h3>Health Profile Complete ✅</h3>
            <p className="profile-complete-status">
              <span className="status-badge status-badge-success">
                <CheckCircle2 size={12} />
                Profile saved
              </span>
            </p>
          </div>
        </div>
        
        <div className="profile-summary">
          {profile?.full_name && (
            <div className="profile-summary-item">
              <span className="summary-label">Name</span>
              <span className="summary-value">{profile.full_name}</span>
            </div>
          )}
          {profile?.sex_at_birth && (
            <div className="profile-summary-item">
              <span className="summary-label">Sex</span>
              <span className="summary-value">{profile.sex_at_birth}</span>
            </div>
          )}
          {(profile?.date_of_birth || profile?.age_years) && (
            <div className="profile-summary-item">
              <span className="summary-label">Age</span>
              <span className="summary-value">
                {profile?.date_of_birth 
                  ? calculateAge(profile.date_of_birth as string)
                  : profile?.age_years
                }
              </span>
            </div>
          )}
          {profile?.height_cm && profile?.weight_kg && (
            <div className="profile-summary-item">
              <span className="summary-label">BMI</span>
              <span className="summary-value">
                {(profile.weight_kg / Math.pow(profile.height_cm / 100, 2)).toFixed(1)}
              </span>
            </div>
          )}
        </div>
        
        <div className="profile-card-footer">
          <button 
            className="profile-card-btn profile-card-btn-secondary"
            onClick={handleEditProfile}
          >
            <Settings size={16} />
            Edit Profile
          </button>
        </div>
      </motion.div>
    );
  }
  
  // IN-PROGRESS - Show resume prompt
  if (inProgress) {
    return (
      <motion.div 
        className="profile-card profile-card-progress"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="profile-card-header">
          <div className="profile-card-icon">
            <Activity size={24} />
          </div>
          <div>
            <h3>Continue your health profile</h3>
            <p>You're {completionScore.toFixed(0)}% complete</p>
          </div>
        </div>
        
        <div className="profile-progress-bar">
          <div 
            className="profile-progress-fill"
            style={{ width: `${completionScore}%` }}
          />
        </div>
        
        <div className="profile-card-actions">
          <button 
            className="profile-card-btn profile-card-btn-primary"
            onClick={handleGetStarted}
          >
            Resume
            <ChevronRight size={18} />
          </button>
        </div>
      </motion.div>
    );
  }
  
  // NOT STARTED - Show CTA
  return (
    <motion.div 
      className="profile-card profile-card-new"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="profile-card-header">
        <div className="profile-card-icon">
          <Heart size={28} />
        </div>
        <div>
          <h3>Complete your health profile</h3>
          <p>Get personalized health insights and recommendations</p>
        </div>
      </div>
      
      <ul className="profile-card-benefits">
        <li>
          <CheckCircle2 size={16} />
          <span>Personalized health recommendations</span>
        </li>
        <li>
          <CheckCircle2 size={16} />
          <span>Better analysis of your reports</span>
        </li>
        <li>
          <CheckCircle2 size={16} />
          <span>Track health trends over time</span>
        </li>
      </ul>
      
      <div className="profile-card-actions">
        <button 
          className="profile-card-btn profile-card-btn-primary"
          onClick={handleGetStarted}
        >
          Get Started
          <ChevronRight size={18} />
        </button>
      </div>
    </motion.div>
  );
}

function calculateAge(dateOfBirth: string): number {
  const dob = new Date(dateOfBirth);
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
    age--;
  }
  return age;
}
