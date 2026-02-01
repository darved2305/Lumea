/**
 * Health Profile Card Component
 * 
 * Shows profile status:
 * - First-time user: "Complete your health profile" CTA
 * - Existing user: Profile summary with edit button
 * - In-progress: Resume wizard prompt
 * - Completed: Success state with View/Edit button
 * 
 * Navigates to /health-profile route.
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
import { fetchFullProfile, FullProfile } from '../../services/profileApi';
import './HealthProfileCard.css';

interface HealthProfileCardProps {
  onProfileUpdated?: () => void;
}

export default function HealthProfileCard({ onProfileUpdated: _onProfileUpdated }: HealthProfileCardProps) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<FullProfile | null>(null);
  
  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFullProfile();
      setProfile(data);
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    loadProfile();
  }, [loadProfile]);
  
  const handleOpenWizard = () => {
    navigate('/health-profile');
  };
  
  // Determine profile state
  const hasProfile = !!profile?.profile;
  const isComplete = profile?.profile?.wizard_completed || false;
  const inProgress = hasProfile && !isComplete && (profile?.profile?.wizard_current_step || 1) > 1;
  const completionScore = profile?.completion?.score || 0;
  
  // Loading state
  if (loading) {
    return (
      <div className="profile-card profile-card-loading">
        <Loader2 className="animate-spin" size={24} />
        <span>Loading profile...</span>
      </div>
    );
  }
  
  // First-time user - show CTA
  if (!hasProfile || (!isComplete && !inProgress)) {
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
            onClick={handleOpenWizard}
          >
            Get Started
            <ChevronRight size={18} />
          </button>
        </div>
      </motion.div>
    );
  }
  
  // In-progress - show resume prompt
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
            onClick={handleOpenWizard}
          >
            Resume
            <ChevronRight size={18} />
          </button>
        </div>
      </motion.div>
    );
  }
  
  // Complete - show success state with summary
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
          <h3>Health Profile Complete</h3>
          <p className="profile-complete-status">
            <span className="status-badge status-badge-success">
              <CheckCircle2 size={12} />
              {completionScore.toFixed(0)}% complete
            </span>
          </p>
        </div>
        <button 
          className="profile-edit-btn"
          onClick={handleOpenWizard}
          title="View & Edit profile"
        >
          <Settings size={16} />
        </button>
      </div>
      
      <div className="profile-summary">
        {profile?.profile?.sex_at_birth && (
          <div className="profile-summary-item">
            <span className="summary-label">Sex</span>
            <span className="summary-value">{profile.profile.sex_at_birth}</span>
          </div>
        )}
        {(profile?.profile?.date_of_birth || profile?.profile?.age_years) && (
          <div className="profile-summary-item">
            <span className="summary-label">Age</span>
            <span className="summary-value">
              {profile.profile?.date_of_birth 
                ? calculateAge(profile.profile.date_of_birth)
                : profile.profile?.age_years
              }
            </span>
          </div>
        )}
        {profile?.derived_features?.find(f => f.feature_name === 'bmi') && (
          <div className="profile-summary-item">
            <span className="summary-label">BMI</span>
            <span className="summary-value">
              {profile.derived_features.find(f => f.feature_name === 'bmi')?.feature_value?.value?.toFixed(1)}
            </span>
          </div>
        )}
        {profile?.conditions && profile.conditions.length > 0 && (
          <div className="profile-summary-item">
            <span className="summary-label">Conditions</span>
            <span className="summary-value">{profile.conditions.length}</span>
          </div>
        )}
      </div>
      
      <div className="profile-card-footer">
        <button 
          className="profile-card-btn profile-card-btn-secondary"
          onClick={handleOpenWizard}
        >
          <Edit2 size={16} />
          View & Edit Profile
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
