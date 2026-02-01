/**
 * Health Profile Form Schema
 * 
 * Defines the wizard steps and questions for the health profile form.
 * Rendered dynamically to allow future extensibility.
 */

export type FieldType = 
  | 'text'
  | 'number'
  | 'date'
  | 'select'
  | 'multiselect'
  | 'radio'
  | 'list'  // For medications, allergies, etc.
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
  required?: boolean;
  placeholder?: string;
  helpText?: string;
  unit?: string;
  min?: number;
  max?: number;
  showIf?: {
    questionId: string;
    values: string[];
  };
  supportsUnknown?: boolean;
  supportsSkip?: boolean;
  essential?: boolean;  // Affects completion score weighting
}

export interface WizardStep {
  id: string;
  title: string;
  description: string;
  fields: FormField[];
}

export const PROFILE_FORM_SCHEMA: WizardStep[] = [
  {
    id: 'basics',
    title: 'Basic Information',
    description: 'Tell us a bit about yourself',
    fields: [
      {
        questionId: 'full_name',
        label: 'Full Name',
        type: 'text',
        placeholder: 'Enter your full name',
        supportsSkip: true,
      },
      {
        questionId: 'date_of_birth',
        label: 'Date of Birth',
        type: 'date',
        helpText: 'Your age helps personalize health recommendations',
        supportsUnknown: true,
        essential: true,
      },
      {
        questionId: 'age_years',
        label: 'Age (if DOB unknown)',
        type: 'number',
        min: 0,
        max: 120,
        unit: 'years',
        showIf: {
          questionId: 'date_of_birth',
          values: ['unknown'],
        },
        supportsUnknown: true,
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
        supportsUnknown: true,
        essential: true,
      },
      {
        questionId: 'gender',
        label: 'Gender Identity',
        type: 'text',
        placeholder: 'Optional',
        supportsSkip: true,
      },
      {
        questionId: 'city',
        label: 'City',
        type: 'text',
        placeholder: 'Your city (optional)',
        supportsSkip: true,
      },
    ],
  },
  {
    id: 'measurements',
    title: 'Body Measurements',
    description: 'Physical measurements help calculate health metrics',
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
        supportsUnknown: true,
        essential: true,
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
        supportsUnknown: true,
        essential: true,
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
        supportsUnknown: true,
        supportsSkip: true,
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
        supportsUnknown: true,
        essential: true,
      },
    ],
  },
  {
    id: 'conditions',
    title: 'Medical Conditions',
    description: 'Help us understand your health background',
    fields: [
      {
        questionId: 'diagnosed_conditions',
        label: 'Diagnosed Conditions',
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
        essential: true,
      },
      {
        questionId: 'conditions_other',
        label: 'Other Conditions',
        type: 'textarea',
        placeholder: 'List any other conditions not mentioned above',
        supportsSkip: true,
      },
      {
        questionId: 'recurring_symptoms',
        label: 'Recurring Symptoms',
        type: 'multiselect',
        options: [
          { value: 'fatigue', label: 'Fatigue' },
          { value: 'headaches', label: 'Headaches' },
          { value: 'joint_pain', label: 'Joint Pain' },
          { value: 'digestive_issues', label: 'Digestive Issues' },
          { value: 'sleep_problems', label: 'Sleep Problems' },
          { value: 'anxiety', label: 'Anxiety' },
          { value: 'other', label: 'Other (specify)' },
          { value: 'none', label: 'None' },
        ],
        helpText: 'Select symptoms you experience regularly',
        supportsSkip: true,
      },
      {
        questionId: 'symptoms_notes',
        label: 'Additional Notes on Symptoms',
        type: 'textarea',
        placeholder: 'Describe any other symptoms',
        supportsSkip: true,
      },
    ],
  },
  {
    id: 'medications',
    title: 'Medications & Allergies',
    description: 'Current medications and known allergies',
    fields: [
      {
        questionId: 'taking_medications',
        label: 'Are you currently taking any medications?',
        type: 'radio',
        options: [
          { value: 'yes', label: 'Yes' },
          { value: 'no', label: 'No' },
        ],
        supportsUnknown: true,
        essential: true,
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
        supportsSkip: true,
      },
      {
        questionId: 'has_allergies',
        label: 'Do you have any known allergies?',
        type: 'radio',
        options: [
          { value: 'yes', label: 'Yes' },
          { value: 'no', label: 'No' },
        ],
        supportsUnknown: true,
        essential: true,
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
      },
    ],
  },
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
        ],
        supportsUnknown: true,
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
      },
      {
        questionId: 'genetic_tests_any',
        label: 'Have you had any genetic testing?',
        type: 'radio',
        options: [
          { value: 'yes', label: 'Yes' },
          { value: 'no', label: 'No' },
        ],
        supportsUnknown: true,
        showIf: {
          questionId: 'family_history_any',
          values: ['yes'],
        },
      },
      {
        questionId: 'genetic_tests_list',
        label: 'Known Genetic Mutations',
        type: 'list',
        listConfig: {
          fields: [
            { 
              name: 'mutation_name', 
              label: 'Mutation', 
              type: 'select',
              required: true,
              options: [
                { value: 'BRCA1', label: 'BRCA1' },
                { value: 'BRCA2', label: 'BRCA2' },
                { value: 'APOE4', label: 'APOE4' },
                { value: 'Factor_V_Leiden', label: 'Factor V Leiden' },
                { value: 'other', label: 'Other' },
              ]
            },
            { 
              name: 'result', 
              label: 'Result', 
              type: 'select',
              options: [
                { value: 'positive', label: 'Positive' },
                { value: 'negative', label: 'Negative' },
                { value: 'variant_uncertain', label: 'Variant of Uncertain Significance' },
              ]
            },
          ],
        },
        showIf: {
          questionId: 'genetic_tests_any',
          values: ['yes'],
        },
      },
    ],
  },
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
        supportsUnknown: true,
        essential: true,
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
        supportsUnknown: true,
        essential: true,
      },
      {
        questionId: 'sleep_hours_avg',
        label: 'Average Hours of Sleep',
        type: 'number',
        min: 0,
        max: 24,
        unit: 'hours',
        placeholder: 'e.g., 7',
        supportsUnknown: true,
        supportsSkip: true,
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
        supportsUnknown: true,
        supportsSkip: true,
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
        supportsUnknown: true,
        supportsSkip: true,
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
        supportsUnknown: true,
        supportsSkip: true,
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
