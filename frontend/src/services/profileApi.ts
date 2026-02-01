/**
 * Profile API Service
 * 
 * Handles all API calls for the health profile feature.
 */

const API_BASE = 'http://localhost:8000';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
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
    const response = await fetch(`${API_BASE}/api/profile`, {
      headers: getAuthHeaders(),
    });
    
    if (response.status === 401) {
      return null;
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch profile: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching profile:', error);
    return null;
  }
}

export async function updateProfile(data: Partial<UserProfile>): Promise<UserProfile | null> {
  try {
    const response = await fetch(`${API_BASE}/api/profile`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update profile: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error updating profile:', error);
    return null;
  }
}

export async function upsertAnswers(answers: { question_id: string; answer_data: AnswerData }[]): Promise<ProfileAnswer[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/answers`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ answers }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save answers: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving answers:', error);
    return [];
  }
}

export async function setConditions(conditions: { condition_code: string; condition_name?: string }[]): Promise<ProfileCondition[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/conditions`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ conditions }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save conditions: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving conditions:', error);
    return [];
  }
}

export async function setSymptoms(symptoms: { symptom_code: string; symptom_name?: string }[]): Promise<ProfileSymptom[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/symptoms`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ symptoms }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save symptoms: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving symptoms:', error);
    return [];
  }
}

export async function setMedications(medications: { name: string; dose?: string; frequency?: string }[]): Promise<ProfileMedication[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/medications`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ medications }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save medications: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving medications:', error);
    return [];
  }
}

export async function setSupplements(supplements: { name: string; dose?: string; frequency?: string }[]): Promise<ProfileSupplement[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/supplements`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ supplements }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save supplements: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving supplements:', error);
    return [];
  }
}

export async function setAllergies(allergies: { allergen: string; allergy_type?: string; reaction?: string; severity?: string }[]): Promise<ProfileAllergy[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/allergies`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ allergies }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save allergies: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving allergies:', error);
    return [];
  }
}

export async function setFamilyHistory(history: { relative_type: string; condition_code: string; age_at_diagnosis?: number }[]): Promise<ProfileFamilyHistory[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/family-history`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ history }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save family history: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error saving family history:', error);
    return [];
  }
}

export async function setGeneticTests(tests: { mutation_name: string; result?: string }[]): Promise<ProfileGeneticTest[]> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/genetic-tests`, {
      method: 'POST',
      headers: getAuthHeaders(),
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
  try {
    const response = await fetch(`${API_BASE}/api/profile/wizard-state`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ current_step: currentStep, completed }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update wizard state: ${response.status}`);
    }
  } catch (error) {
    console.error('Error updating wizard state:', error);
  }
}

export async function triggerRecompute(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/profile/recompute`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to trigger recompute: ${response.status}`);
    }
  } catch (error) {
    console.error('Error triggering recompute:', error);
  }
}
