/**
 * useProfileRequired Hook
 * 
 * Hook to check if user has completed their health profile.
 * Redirects to /health-profile if required fields are missing.
 * 
 * Usage:
 * const { loading, profileComplete } = useProfileRequired();
 * 
 * Set `redirect: true` to auto-redirect incomplete profiles.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { fetchFullProfile, FullProfile } from '../services/profileApi';
import { REQUIRED_FIELDS } from '../components/profile/profileFormSchema';
import { getTokenSync } from '../services/tokenService';

interface UseProfileRequiredOptions {
  redirect?: boolean;        // Auto-redirect if profile incomplete
  requiredFields?: string[]; // Override default required fields
}

interface UseProfileRequiredReturn {
  loading: boolean;
  profile: FullProfile | null;
  profileComplete: boolean;
  requiredFieldsMissing: string[];
  checkProfile: () => Promise<void>;
}

export default function useProfileRequired(
  options: UseProfileRequiredOptions = {}
): UseProfileRequiredReturn {
  const { redirect = false, requiredFields = REQUIRED_FIELDS } = options;

  const navigate = useNavigate();
  const location = useLocation();

  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<FullProfile | null>(null);
  const [profileComplete, setProfileComplete] = useState(false);
  const [requiredFieldsMissing, setRequiredFieldsMissing] = useState<string[]>([]);

  const checkProfile = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFullProfile();
      setProfile(data);

      // Check if required fields are filled
      const missing: string[] = [];

      if (data?.profile) {
        const p = data.profile;

        for (const field of requiredFields) {
          const value = (p as any)[field];
          if (value === null || value === undefined || value === '') {
            missing.push(field);
          }
        }
      } else {
        // No profile at all - all required fields missing
        missing.push(...requiredFields);
      }

      const isComplete = missing.length === 0;
      setProfileComplete(isComplete);
      setRequiredFieldsMissing(missing);

      // Redirect if needed and not already on health profile page
      if (redirect && !isComplete && location.pathname !== '/health-profile') {
        navigate('/health-profile', {
          state: { from: location.pathname, reason: 'profile_incomplete' }
        });
      }

    } catch (error) {
      console.error('Error checking profile:', error);
      // On error, assume profile is incomplete if redirect is enabled
      if (redirect) {
        setProfileComplete(false);
        setRequiredFieldsMissing(requiredFields);
      }
    } finally {
      setLoading(false);
    }
  }, [navigate, location, redirect, requiredFields]);

  useEffect(() => {
    // Only check if user is authenticated
    const token = getTokenSync();
    if (token) {
      checkProfile();
    } else {
      setLoading(false);
      setProfileComplete(false);
    }
  }, [checkProfile]);

  return {
    loading,
    profile,
    profileComplete,
    requiredFieldsMissing,
    checkProfile,
  };
}
