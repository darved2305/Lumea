/**
 * Profile API Service
 * 
 * Handles all API calls for the health profile feature.
 */
import { API_BASE_URL } from '../config/api';

const API_BASE = API_BASE_URL;

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else {
    console.warn('profileApi: No access_token found in localStorage');
  }
  
  return headers;
}

// Types
export interface AnswerData {
  value: any;
  unit?: string;
  unknown: boolean;
  skipped: boolean;
}

export interface ProfileAnswer {
  question_id: string;
  answer_data: AnswerData;
  updated_at: string;
}

export interface ProfileCondition {
  id: string;
  condition_code: string;
  condition_name?: string;
  diagnosed_at?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
}

export interface ProfileSymptom {
  id: string;
  symptom_code: string;
  symptom_name?: string;
  frequency?: string;
  severity?: string;
  notes?: string;
  created_at: string;
}

export interface ProfileMedication {
  id: string;
  name: string;
  dose?: string;
  frequency?: string;
  started_at?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
}

export interface ProfileSupplement {
  id: string;
  name: string;
  dose?: string;
  frequency?: string;
  is_active: boolean;
  created_at: string;
}

export interface ProfileAllergy {
  id: string;
  allergen: string;
  allergy_type?: string;
  reaction?: string;
  severity?: string;
  notes?: string;
  created_at: string;
}

export interface ProfileFamilyHistory {
  id: string;
  relative_type: string;
  condition_code: string;
  condition_name?: string;
  age_at_diagnosis?: number;
  notes?: string;
  created_at: string;
}

export interface ProfileGeneticTest {
  id: string;
  mutation_name: string;
  result?: string;
  test_date?: string;
  lab_name?: string;
  notes?: string;
  created_at: string;
}

export interface DerivedFeature {
  feature_name: string;
  feature_value: Record<string, any>;
  computed_at: string;
}

export interface ProfileCompletion {
  score: number;
  missing_essentials: string[];
  missing_optional: string[];
  estimated_fields: string[];
  completion_by_step: Record<string, number>;
}

export interface UserProfile {
  id: string;
  user_id: string;
  full_name?: string;
  date_of_birth?: string;
  age_years?: number;
  sex_at_birth?: string;
  gender?: string;
  city?: string;
  height_cm?: number;
  weight_kg?: number;
  waist_cm?: number;
  activity_level?: string;
  smoking?: string;
  alcohol?: string;
  sleep_hours_avg?: number;
  sleep_quality?: string;
  exercise_minutes_per_week?: number;
  diet_pattern?: string;
  wizard_current_step: number;
  wizard_completed: boolean;
  wizard_last_saved_at?: string;
  is_completed?: boolean;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface FullProfile {
  profile: UserProfile | null;
  answers: ProfileAnswer[];
  conditions: ProfileCondition[];
  symptoms: ProfileSymptom[];
  medications: ProfileMedication[];
  supplements: ProfileSupplement[];
  allergies: ProfileAllergy[];
  family_history: ProfileFamilyHistory[];
  genetic_tests: ProfileGeneticTest[];
  derived_features: DerivedFeature[];
  completion: ProfileCompletion;
}

// API Functions

export async function fetchFullProfile(): Promise<FullProfile | null> {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.warn('fetchFullProfile: No auth token, skipping fetch');
      return null;
    }
    
    const response = await fetch(`${API_BASE}/api/profile`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    
    if (response.status === 401) {
      console.warn('fetchFullProfile: 401 Unauthorized');
      return null;
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch profile: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching profile:', error);
    throw error;
  }
}

export async function updateProfile(data: Partial<UserProfile>): Promise<UserProfile | null> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Not authenticated - no token');
  }
  
  // Clean up data - remove undefined values that backend might reject
  const cleanData: Record<string, any> = {};
  for (const [key, value] of Object.entries(data)) {
    if (value !== undefined) {
      cleanData[key] = value;
    }
  }
  
  console.log('updateProfile: Sending PATCH with data:', cleanData);
  
  const response = await fetch(`${API_BASE}/api/profile`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(cleanData),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    console.error('updateProfile: Error response:', errorData);
    // Handle both string and array detail formats from FastAPI
    let errorMessage = `Failed to update profile: ${response.status}`;
    if (errorData.detail) {
      if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
      } else if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else {
        errorMessage = JSON.stringify(errorData.detail);
      }
    }
    throw new Error(errorMessage);
  }
  
  const result = await response.json();
  console.log('updateProfile: Success');
  return result;
}

export async function upsertAnswers(answers: { question_id: string; answer_data: AnswerData }[]): Promise<ProfileAnswer[]> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_BASE}/api/profile/answers`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ answers }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const detail = Array.isArray(errorData.detail) 
      ? errorData.detail.map((e: any) => e.msg || e).join(', ')
      : (errorData.detail || `Failed to save answers: ${response.status}`);
    throw new Error(detail);
  }
  
  return await response.json();
}

export async function setConditions(conditions: { condition_code: string; condition_name?: string }[]): Promise<ProfileCondition[]> {
  const response = await fetch(`${API_BASE}/api/profile/conditions`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ conditions }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save conditions: ${response.status}`);
  }
  
  return await response.json();
}

export async function setSymptoms(symptoms: { symptom_code: string; symptom_name?: string }[]): Promise<ProfileSymptom[]> {
  const response = await fetch(`${API_BASE}/api/profile/symptoms`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ symptoms }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save symptoms: ${response.status}`);
  }
  
  return await response.json();
}

export async function setMedications(medications: { name: string; dose?: string; frequency?: string }[]): Promise<ProfileMedication[]> {
  const response = await fetch(`${API_BASE}/api/profile/medications`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ medications }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save medications: ${response.status}`);
  }
  
  return await response.json();
}

export async function setSupplements(supplements: { name: string; dose?: string; frequency?: string }[]): Promise<ProfileSupplement[]> {
  const response = await fetch(`${API_BASE}/api/profile/supplements`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ supplements }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save supplements: ${response.status}`);
  }
  
  return await response.json();
}

export async function setAllergies(allergies: { allergen: string; allergy_type?: string; reaction?: string; severity?: string }[]): Promise<ProfileAllergy[]> {
  const response = await fetch(`${API_BASE}/api/profile/allergies`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ allergies }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save allergies: ${response.status}`);
  }
  
  return await response.json();
}

export async function setFamilyHistory(history: { relative_type: string; condition_code: string; age_at_diagnosis?: number }[]): Promise<ProfileFamilyHistory[]> {
  const response = await fetch(`${API_BASE}/api/profile/family-history`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ history }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save family history: ${response.status}`);
  }
  
  return await response.json();
}

export async function setGeneticTests(tests: { mutation_name: string; result?: string }[]): Promise<ProfileGeneticTest[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/genetic-tests`, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'include',
      body: JSON.stringify({ tests }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save genetic tests: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving genetic tests:', error);
    return [];
  }
}

export async function fetchCompletion(): Promise<ProfileCompletion | null> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/completion`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch completion: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching completion:', error);
    return null;
  }
}

export async function updateWizardState(currentStep: number, completed?: boolean): Promise<void> {
  const response = await fetch(`${API_BASE}/api/profile/wizard-state`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ current_step: currentStep, completed }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update wizard state: ${response.status}`);
  }
}

export async function triggerRecompute(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/recompute`, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to trigger recompute: ${response.status}`);
    }
  } catch (error) {
    console.error('Error triggering recompute:', error);
  }
}


// ============================================================================
// PROFILE /ME ENDPOINTS (Simplified for Reports page)
// ============================================================================

export interface ProfileMeResponse {
  exists: boolean;
  is_completed: boolean;
  profile: UserProfile | null;
  completion: ProfileCompletion | null;
}

/**
 * Get profile status - used by Reports page to determine if profile is complete.
 * Returns exists=false for new users, is_completed=true when all required fields filled.
 */
export async function fetchProfileMe(): Promise<ProfileMeResponse> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    console.warn('fetchProfileMe: No auth token');
    return { exists: false, is_completed: false, profile: null, completion: null };
  }
  
  try {
    const response = await fetch(`${API_BASE}/api/profile/me`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    
    if (response.status === 401) {
      console.warn('fetchProfileMe: Unauthorized');
      return { exists: false, is_completed: false, profile: null, completion: null };
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch profile: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching profile/me:', error);
    throw error;
  }
}

/**
 * Create or update profile (UPSERT) - used by Health Profile form.
 * Sets is_completed=true when all required fields are present.
 */
export async function upsertProfileMe(data: Partial<UserProfile>): Promise<UserProfile> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Not authenticated - no token');
  }
  
  // Clean data
  const cleanData: Record<string, any> = {};
  for (const [key, value] of Object.entries(data)) {
    if (value !== undefined) {
      cleanData[key] = value;
    }
  }
  
  console.log('upsertProfileMe: Sending PUT with data:', cleanData);
  
  const response = await fetch(`${API_BASE}/api/profile/me`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(cleanData),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    console.error('upsertProfileMe: Error response:', errorData);
    let errorMessage = `Failed to save profile: ${response.status}`;
    if (errorData.detail) {
      if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
      } else if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      }
    }
    throw new Error(errorMessage);
  }
  
  const result = await response.json();
  console.log('upsertProfileMe: Success, is_completed:', result.is_completed);
  return result;
}

/**
 * Partial update for profile - used by Settings page for edits.
 */
export async function patchProfileMe(data: Partial<UserProfile>): Promise<UserProfile> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Not authenticated - no token');
  }
  
  const cleanData: Record<string, any> = {};
  for (const [key, value] of Object.entries(data)) {
    if (value !== undefined) {
      cleanData[key] = value;
    }
  }
  
  const response = await fetch(`${API_BASE}/api/profile/me`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(cleanData),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update profile: ${response.status}`);
  }
  
  return await response.json();
}


// ============================================================================
// REMINDER API
// ============================================================================

export interface Reminder {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message?: string;
  schedule_type: string;
  schedule_json: Record<string, any>;
  timezone: string;
  next_run_at?: string;
  last_run_at?: string;
  is_enabled: boolean;
  channel: string;
  medicine_id?: string;
  medicine_name?: string;
  created_at: string;
  updated_at: string;
}

export interface ReminderCreate {
  type: string;
  title: string;
  message?: string;
  schedule_type: string;
  schedule_json: {
    times?: string[];
    interval_minutes?: number;
    start_time?: string;
    end_time?: string;
    cron?: string;
  };
  timezone?: string;
  channel?: string;
  medicine_id?: string;
  medicine_name?: string;
  is_enabled?: boolean;
}

export async function fetchReminders(): Promise<Reminder[]> {
  const token = localStorage.getItem('access_token');
  if (!token) return [];
  
  const response = await fetch(`${API_BASE}/api/reminders/me`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (!response.ok) {
    console.error('Failed to fetch reminders:', response.status);
    return [];
  }
  
  return await response.json();
}

export async function createReminder(data: ReminderCreate): Promise<Reminder> {
  const response = await fetch(`${API_BASE}/api/reminders`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create reminder: ${response.status}`);
  }
  
  return await response.json();
}

export async function updateReminder(id: string, data: Partial<ReminderCreate>): Promise<Reminder> {
  const response = await fetch(`${API_BASE}/api/reminders/${id}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update reminder: ${response.status}`);
  }
  
  return await response.json();
}

export async function deleteReminder(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/reminders/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete reminder: ${response.status}`);
  }
}

export async function generateDefaultReminders(): Promise<Reminder[]> {
  const response = await fetch(`${API_BASE}/api/reminders/generate-default`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to generate reminders: ${response.status}`);
  }
  
  return await response.json();
}
