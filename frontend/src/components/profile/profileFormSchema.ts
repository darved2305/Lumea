/**
 * Health Profile Form Schema
 * 
 * Defines the wizard steps and questions for the health profile form.
 * 
 * Production-ready version:
 * - Removed supportsSkip/supportsUnknown (compulsory form)
 * - Removed duplicate "Other" textareas (inline only)
 * - Added required flag for mandatory fields
 * - Added gridColumn hints for 2-column layout
 * - Split into 8 steps for less scrolling per step
 */

export type FieldType = 
  | 'text'
  | 'number'
  | 'date'
  | 'select'
  | 'multiselect'
  | 'radio'
  | 'list'
  | 'textarea';

export interface FieldOption {
  value: string;
  label: string;
}

export interface ListFieldConfig {
  fields: {
    name: string;
    label: string;
    type: 'text' | 'number' | 'select';
    options?: FieldOption[];
    required?: boolean;
  }[];
}

export interface FormField {
  questionId: string;
  label: string;
  type: FieldType;
  options?: FieldOption[];
  listConfig?: ListFieldConfig;
  required?: boolean;       // If true, must be filled to proceed
  placeholder?: string;
  helpText?: string;
  unit?: string;
  min?: number;
  max?: number;
  showIf?: {
    questionId: string;
    values: string[];
  };
  gridColumn?: 'half' | 'full';  // Layout hint for 2-column grid
}

export interface WizardStep {
  id: string;
  title: string;
  description: string;
  fields: FormField[];
}

// Required fields that block progress
export const REQUIRED_FIELDS = [
  'date_of_birth',
  'sex_at_birth',
  'height_cm',
  'weight_kg',
];

export const PROFILE_FORM_SCHEMA: WizardStep[] = [
  // STEP 1: Basic Info
  {
    id: 'basics',
    title: 'Basic Information',
    description: 'Let\'s start with some essential details',
    fields: [
      {
        questionId: 'full_name',
        label: 'Full Name',
        type: 'text',
        placeholder: 'Enter your full name',
        gridColumn: 'full',
      },
      {
        questionId: 'date_of_birth',
        label: 'Date of Birth',
        type: 'date',
        helpText: 'Your age helps personalize health recommendations',
        required: true,
        gridColumn: 'half',
      },
      {
        questionId: 'sex_at_birth',
        label: 'Sex at Birth',
        type: 'radio',
        options: [
          { value: 'male', label: 'Male' },
          { value: 'female', label: 'Female' },
          { value: 'intersex', label: 'Intersex' },
          { value: 'prefer_not', label: 'Prefer not to say' },
        ],
        helpText: 'Biological sex affects reference ranges for lab values',
        required: true,
        gridColumn: 'half',
      },
      {
        questionId: 'city',
        label: 'City',
        type: 'text',
        placeholder: 'Your city (optional)',
        gridColumn: 'half',
      },
    ],
  },
  
  // STEP 2: Body Measurements
  {
    id: 'measurements',
    title: 'Body Measurements',
    description: 'These measurements help calculate your health metrics',
    fields: [
      {
        questionId: 'height_cm',
        label: 'Height',
        type: 'number',
        min: 50,
        max: 250,
        unit: 'cm',
        placeholder: 'e.g., 170',
        helpText: 'Used to calculate BMI',
        required: true,
        gridColumn: 'half',
      },
      {
        questionId: 'weight_kg',
        label: 'Weight',
        type: 'number',
        min: 20,
        max: 300,
        unit: 'kg',
        placeholder: 'e.g., 70',
        helpText: 'Used to calculate BMI',
        required: true,
        gridColumn: 'half',
      },
      {
        questionId: 'waist_cm',
        label: 'Waist Circumference',
        type: 'number',
        min: 30,
        max: 200,
        unit: 'cm',
        placeholder: 'Optional',
        helpText: 'Measured at navel level',
        gridColumn: 'half',
      },
      {
        questionId: 'activity_level',
        label: 'Activity Level',
        type: 'radio',
        options: [
          { value: 'sedentary', label: 'Sedentary (little to no exercise)' },
          { value: 'moderate', label: 'Moderate (exercise 2-3 times/week)' },
          { value: 'active', label: 'Active (exercise 4+ times/week)' },
        ],
        gridColumn: 'full',
      },
    ],
  },
  
  // STEP 3: Medical Conditions
  {
    id: 'conditions',
    title: 'Medical Conditions',
    description: 'Help us understand your health background',
    fields: [
      {
        questionId: 'diagnosed_conditions',
        label: 'Have you been diagnosed with any of these conditions?',
        type: 'multiselect',
        options: [
          { value: 'diabetes', label: 'Diabetes' },
          { value: 'prediabetes', label: 'Prediabetes' },
          { value: 'high_bp', label: 'High Blood Pressure' },
          { value: 'high_cholesterol', label: 'High Cholesterol' },
          { value: 'thyroid_disorder', label: 'Thyroid Disorder' },
          { value: 'heart_disease', label: 'Heart Disease' },
          { value: 'asthma_copd', label: 'Asthma / COPD' },
          { value: 'kidney_disease', label: 'Kidney Disease' },
          { value: 'liver_disease', label: 'Liver Disease' },
          { value: 'pcos', label: 'PCOS' },
          { value: 'other', label: 'Other (specify)' },
          { value: 'none', label: 'None of the above' },
        ],
        helpText: 'Select all that apply',
        gridColumn: 'full',
      },
    ],
  },
  
  // STEP 4: Symptoms
  {
    id: 'symptoms',
    title: 'Recurring Symptoms',
    description: 'Tell us about any symptoms you experience regularly',
    fields: [
      {
        questionId: 'recurring_symptoms',
        label: 'Do you experience any of these symptoms regularly?',
        type: 'multiselect',
        options: [
          { value: 'fatigue', label: 'Fatigue' },
          { value: 'headaches', label: 'Headaches' },
          { value: 'joint_pain', label: 'Joint Pain' },
          { value: 'digestive_issues', label: 'Digestive Issues' },
          { value: 'sleep_problems', label: 'Sleep Problems' },
          { value: 'anxiety', label: 'Anxiety' },
          { value: 'dizziness', label: 'Dizziness' },
          { value: 'shortness_of_breath', label: 'Shortness of Breath' },
          { value: 'other', label: 'Other (specify)' },
          { value: 'none', label: 'None' },
        ],
        helpText: 'Select all that apply',
        gridColumn: 'full',
      },
    ],
  },
  
  // STEP 5: Medications & Supplements
  {
    id: 'medications',
    title: 'Medications & Supplements',
    description: 'Current medications and supplements you take',
    fields: [
      {
        questionId: 'taking_medications',
        label: 'Are you currently taking any medications?',
        type: 'radio',
        options: [
          { value: 'yes', label: 'Yes' },
          { value: 'no', label: 'No' },
        ],
        gridColumn: 'full',
      },
      {
        questionId: 'medications_list',
        label: 'Medications',
        type: 'list',
        listConfig: {
          fields: [
            { name: 'name', label: 'Medication Name', type: 'text', required: true },
            { name: 'dose', label: 'Dose', type: 'text' },
            { 
              name: 'frequency', 
              label: 'Frequency', 
              type: 'select',
              options: [
                { value: 'once_daily', label: 'Once daily' },
                { value: 'twice_daily', label: 'Twice daily' },
                { value: 'three_times_daily', label: 'Three times daily' },
                { value: 'as_needed', label: 'As needed' },
                { value: 'weekly', label: 'Weekly' },
                { value: 'other', label: 'Other' },
              ]
            },
          ],
        },
        showIf: {
          questionId: 'taking_medications',
          values: ['yes'],
        },
        gridColumn: 'full',
      },
      {
        questionId: 'taking_supplements',
        label: 'Do you take any supplements or vitamins?',
        type: 'radio',
        options: [
          { value: 'yes', label: 'Yes' },
          { value: 'no', label: 'No' },
        ],
        gridColumn: 'full',
      },
      {
        questionId: 'supplements_list',
        label: 'Supplements / Vitamins',
        type: 'list',
        listConfig: {
          fields: [
            { name: 'name', label: 'Supplement Name', type: 'text', required: true },
            { name: 'dose', label: 'Dose', type: 'text' },
          ],
        },
        showIf: {
          questionId: 'taking_supplements',
          values: ['yes'],
        },
        gridColumn: 'full',
      },
    ],
  },
  
  // STEP 6: Allergies
  {
    id: 'allergies',
    title: 'Allergies',
    description: 'Known allergies help us flag potential interactions',
    fields: [
      {
        questionId: 'has_allergies',
        label: 'Do you have any known allergies?',
        type: 'radio',
        options: [
          { value: 'yes', label: 'Yes' },
          { value: 'no', label: 'No' },
        ],
        gridColumn: 'full',
      },
      {
        questionId: 'allergies_list',
        label: 'Allergies',
        type: 'list',
        listConfig: {
          fields: [
            { name: 'allergen', label: 'Allergen', type: 'text', required: true },
            { 
              name: 'allergy_type', 
              label: 'Type', 
              type: 'select',
              options: [
                { value: 'drug', label: 'Drug' },
                { value: 'food', label: 'Food' },
                { value: 'environmental', label: 'Environmental' },
                { value: 'other', label: 'Other' },
              ]
            },
            { name: 'reaction', label: 'Reaction', type: 'text' },
            { 
              name: 'severity', 
              label: 'Severity', 
              type: 'select',
              options: [
                { value: 'mild', label: 'Mild' },
                { value: 'moderate', label: 'Moderate' },
                { value: 'severe', label: 'Severe' },
                { value: 'life_threatening', label: 'Life-threatening' },
              ]
            },
          ],
        },
        showIf: {
          questionId: 'has_allergies',
          values: ['yes'],
        },
        gridColumn: 'full',
      },
    ],
  },
  
  // STEP 7: Family History
  {
    id: 'family_history',
    title: 'Family History',
    description: 'Medical history of close relatives',
    fields: [
      {
        questionId: 'family_history_any',
        label: 'Do any close relatives have significant health conditions?',
        type: 'radio',
        options: [
          { value: 'yes', label: 'Yes' },
          { value: 'no', label: 'No' },
          { value: 'unknown', label: 'I don\'t know' },
        ],
        gridColumn: 'full',
      },
      {
        questionId: 'family_history_list',
        label: 'Family Medical History',
        type: 'list',
        listConfig: {
          fields: [
            { 
              name: 'relative_type', 
              label: 'Relative', 
              type: 'select',
              required: true,
              options: [
                { value: 'mother', label: 'Mother' },
                { value: 'father', label: 'Father' },
                { value: 'sibling', label: 'Sibling' },
                { value: 'grandparent_maternal', label: 'Maternal Grandparent' },
                { value: 'grandparent_paternal', label: 'Paternal Grandparent' },
              ]
            },
            { 
              name: 'condition_code', 
              label: 'Condition', 
              type: 'select',
              required: true,
              options: [
                { value: 'diabetes', label: 'Diabetes' },
                { value: 'heart_disease', label: 'Heart Disease' },
                { value: 'cancer', label: 'Cancer' },
                { value: 'high_bp', label: 'High Blood Pressure' },
                { value: 'stroke', label: 'Stroke' },
                { value: 'alzheimers', label: "Alzheimer's / Dementia" },
                { value: 'other', label: 'Other' },
              ]
            },
            { name: 'age_at_diagnosis', label: 'Age at Diagnosis', type: 'number' },
          ],
        },
        showIf: {
          questionId: 'family_history_any',
          values: ['yes'],
        },
        gridColumn: 'full',
      },
    ],
  },
  
  // STEP 8: Lifestyle
  {
    id: 'lifestyle',
    title: 'Lifestyle',
    description: 'Daily habits and routines',
    fields: [
      {
        questionId: 'smoking',
        label: 'Smoking Status',
        type: 'radio',
        options: [
          { value: 'never', label: 'Never smoked' },
          { value: 'former', label: 'Former smoker' },
          { value: 'current', label: 'Current smoker' },
          { value: 'prefer_not', label: 'Prefer not to say' },
        ],
        gridColumn: 'half',
      },
      {
        questionId: 'alcohol',
        label: 'Alcohol Consumption',
        type: 'radio',
        options: [
          { value: 'none', label: 'None' },
          { value: 'occasional', label: 'Occasional (1-2 drinks/week)' },
          { value: 'frequent', label: 'Frequent (3+ drinks/week)' },
        ],
        gridColumn: 'half',
      },
      {
        questionId: 'sleep_hours_avg',
        label: 'Average Hours of Sleep',
        type: 'number',
        min: 0,
        max: 24,
        unit: 'hours',
        placeholder: 'e.g., 7',
        gridColumn: 'half',
      },
      {
        questionId: 'sleep_quality',
        label: 'Sleep Quality',
        type: 'radio',
        options: [
          { value: 'good', label: 'Good - I feel rested' },
          { value: 'ok', label: 'OK - Could be better' },
          { value: 'poor', label: 'Poor - Often tired' },
        ],
        gridColumn: 'half',
      },
      {
        questionId: 'exercise_minutes_per_week',
        label: 'Exercise per Week',
        type: 'number',
        min: 0,
        max: 10080,
        unit: 'minutes',
        placeholder: 'e.g., 150',
        helpText: 'Total minutes of moderate+ intensity exercise',
        gridColumn: 'half',
      },
      {
        questionId: 'diet_pattern',
        label: 'Diet Pattern',
        type: 'radio',
        options: [
          { value: 'veg', label: 'Vegetarian' },
          { value: 'nonveg', label: 'Non-vegetarian' },
          { value: 'mixed', label: 'Mixed' },
        ],
        gridColumn: 'half',
      },
    ],
  },
];

// Condition codes mapping for display
export const CONDITION_LABELS: Record<string, string> = {
  diabetes: 'Diabetes',
  prediabetes: 'Prediabetes',
  high_bp: 'High Blood Pressure',
  high_cholesterol: 'High Cholesterol',
  thyroid_disorder: 'Thyroid Disorder',
  heart_disease: 'Heart Disease',
  asthma_copd: 'Asthma / COPD',
  kidney_disease: 'Kidney Disease',
  liver_disease: 'Liver Disease',
  pcos: 'PCOS',
};

export const RELATIVE_LABELS: Record<string, string> = {
  mother: 'Mother',
  father: 'Father',
  sibling: 'Sibling',
  grandparent_maternal: 'Maternal Grandparent',
  grandparent_paternal: 'Paternal Grandparent',
};
