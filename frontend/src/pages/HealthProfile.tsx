/**
 * Health Profile Page (Production-Ready)
 * 
 * Full-page wizard for completing health profile.
 * 
 * Features:
 * - Welcome screen with ETA
 * - Multi-step wizard with progress tracking
 * - Autosave with visual feedback
 * - Inline "Other" option for multi-selects
 * - Required field validation with red error messages
 * - Wider 2-column layout for less scrolling
 * - No skip/don't know options (compulsory form)
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronLeft,
  ChevronRight,
  Check,
  Loader2,
  AlertCircle,
  Plus,
  X,
  Clock,
  Heart,
  TrendingUp,
  Shield,
  ArrowLeft
} from 'lucide-react';
import {
  PROFILE_FORM_SCHEMA,
  FormField,
  CONDITION_LABELS,
  REQUIRED_FIELDS
} from '../components/profile/profileFormSchema';
import {
  fetchFullProfile,
  updateProfile,
  upsertAnswers,
  setConditions,
  setSymptoms,
  setMedications,
  setSupplements,
  setAllergies,
  setFamilyHistory,
  updateWizardState,
  AnswerData,
} from '../services/profileApi';
import ProfileSuccessScreen from '../components/ProfileSuccessScreen';
import './HealthProfile.css';

type FormValues = Record<string, AnswerData>;
type ValidationErrors = Record<string, string>;

// Fields that support "Other" option with inline text
const FIELDS_WITH_OTHER = [
  'diagnosed_conditions',
  'recurring_symptoms',
];

export default function HealthProfile() {
  const navigate = useNavigate();

  // Wizard states
  const [showWelcome, setShowWelcome] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [formValues, setFormValues] = useState<FormValues>({});
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [showSuccess, setShowSuccess] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Validation
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [showErrors, setShowErrors] = useState(false);

  // "Other" text values for multi-selects
  const [otherTexts, setOtherTexts] = useState<Record<string, string>>({});

  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedRef = useRef<string>('');

  // Load profile data on mount
  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await fetchFullProfile();
      if (data) {
        // Initialize form values from profile
        const values: FormValues = {};
        const otherTxts: Record<string, string> = {};

        // Load from profile object
        if (data.profile) {
          const p = data.profile;
          const profileFields = [
            'full_name', 'date_of_birth', 'age_years', 'sex_at_birth', 'gender', 'city',
            'height_cm', 'weight_kg', 'waist_cm', 'activity_level',
            'smoking', 'alcohol', 'sleep_hours_avg', 'sleep_quality',
            'exercise_minutes_per_week', 'diet_pattern'
          ];

          for (const field of profileFields) {
            const value = (p as any)[field];
            if (value !== null && value !== undefined) {
              values[field] = { value, unknown: false, skipped: false };
            }
          }

          // Check if returning user (has made progress)
          const hasProgress = (p.wizard_current_step || 1) > 1 || p.wizard_completed;
          if (hasProgress) {
            setShowWelcome(false);
          }

          // Resume from last step
          setCurrentStep(Math.max(0, (p.wizard_current_step || 1) - 1));
        }

        // Load from answers (safely handle missing/null answers)
        const answers = data.answers || [];
        for (const answer of answers) {
          values[answer.question_id] = answer.answer_data;

          // Check for "other" text answers
          if (answer.question_id.endsWith('_other_text')) {
            const baseField = answer.question_id.replace('_other_text', '');
            otherTxts[baseField] = answer.answer_data.value || '';
          }
        }

        // Load conditions as multiselect value
        const conditions = data.conditions || [];
        if (conditions.length > 0) {
          const codes = conditions.map(c => c.condition_code);
          // Check if any are "other" type
          const hasOther = conditions.some(c => c.condition_code === 'other');
          const otherCondition = conditions.find(c => c.condition_code === 'other');
          if (hasOther && otherCondition?.condition_name !== 'Other') {
            otherTxts['diagnosed_conditions'] = otherCondition?.condition_name || '';
          }
          values['diagnosed_conditions'] = {
            value: codes,
            unknown: false,
            skipped: false
          };
        }

        // Load symptoms as multiselect value
        if (data.symptoms.length > 0) {
          const codes = data.symptoms.map(s => s.symptom_code);
          const hasOther = data.symptoms.some(s => s.symptom_code === 'other');
          const otherSymptom = data.symptoms.find(s => s.symptom_code === 'other');
          if (hasOther && otherSymptom?.notes) {
            otherTxts['recurring_symptoms'] = otherSymptom.notes || '';
          }
          values['recurring_symptoms'] = {
            value: codes,
            unknown: false,
            skipped: false
          };
        }

        // Load medications
        if (data.medications.length > 0) {
          values['taking_medications'] = { value: 'yes', unknown: false, skipped: false };
          values['medications_list'] = {
            value: data.medications.map(m => ({
              name: m.name,
              dose: m.dose || '',
              frequency: m.frequency || ''
            })),
            unknown: false,
            skipped: false
          };
        }

        // Load supplements
        if (data.supplements.length > 0) {
          values['supplements_list'] = {
            value: data.supplements.map(s => ({
              name: s.name,
              dose: s.dose || ''
            })),
            unknown: false,
            skipped: false
          };
        }

        // Load allergies
        if (data.allergies.length > 0) {
          values['has_allergies'] = { value: 'yes', unknown: false, skipped: false };
          values['allergies_list'] = {
            value: data.allergies.map(a => ({
              allergen: a.allergen,
              allergy_type: a.allergy_type || '',
              reaction: a.reaction || '',
              severity: a.severity || ''
            })),
            unknown: false,
            skipped: false
          };
        }

        // Load family history
        if (data.family_history.length > 0) {
          values['family_history_any'] = { value: 'yes', unknown: false, skipped: false };
          values['family_history_list'] = {
            value: data.family_history.map(f => ({
              relative_type: f.relative_type,
              condition_code: f.condition_code,
              age_at_diagnosis: f.age_at_diagnosis || ''
            })),
            unknown: false,
            skipped: false
          };
        }

        setFormValues(values);
        setOtherTexts(otherTxts);
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // COMPLETION PERCENTAGE CALCULATION
  // ============================================
  const completionPercent = useMemo(() => {
    let totalFields = 0;
    let answeredFields = 0;

    // Go through all fields in all steps
    for (const step of PROFILE_FORM_SCHEMA) {
      for (const field of step.fields) {
        // Skip conditional fields if their condition isn't met
        if (field.showIf) {
          const dependencyValue = formValues[field.showIf.questionId];
          if (!dependencyValue) continue;

          if (Array.isArray(dependencyValue.value)) {
            if (!field.showIf.values.some(v => dependencyValue.value.includes(v))) continue;
          } else {
            if (!field.showIf.values.includes(dependencyValue.value)) continue;
          }
        }

        totalFields += 1;

        // Check if field is answered
        const answer = formValues[field.questionId];
        if (answer && answer.value !== null && answer.value !== undefined && answer.value !== '') {
          if (Array.isArray(answer.value)) {
            if (answer.value.length > 0) {
              answeredFields += 1;
            }
          } else {
            answeredFields += 1;
          }
        }
      }
    }

    if (totalFields === 0) return 0;
    return Math.round((answeredFields / totalFields) * 100);
  }, [formValues]);

  // ============================================
  // VALIDATION
  // ============================================
  const validateCurrentStep = useCallback((): boolean => {
    const currentStepData = PROFILE_FORM_SCHEMA[currentStep];
    const errors: ValidationErrors = {};

    for (const field of currentStepData.fields) {
      // Skip conditional fields if their condition isn't met
      if (field.showIf) {
        const dependencyValue = formValues[field.showIf.questionId];
        if (!dependencyValue) continue;

        if (Array.isArray(dependencyValue.value)) {
          if (!field.showIf.values.some(v => dependencyValue.value.includes(v))) continue;
        } else {
          if (!field.showIf.values.includes(dependencyValue.value)) continue;
        }
      }

      // Check required fields
      if (field.required || REQUIRED_FIELDS.includes(field.questionId)) {
        const answer = formValues[field.questionId];
        const isEmpty = !answer ||
          answer.value === null ||
          answer.value === undefined ||
          answer.value === '' ||
          (Array.isArray(answer.value) && answer.value.length === 0);

        if (isEmpty) {
          errors[field.questionId] = `${field.label} is required`;
        }
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [currentStep, formValues]);

  // Debounced autosave
  const debouncedSave = useCallback((values: FormValues, otherTxts: Record<string, string>) => {
    // Don't autosave if there's already a save error
    if (saveStatus === 'error') {
      return;
    }

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    const valuesJson = JSON.stringify({ values, otherTxts });
    if (valuesJson === lastSavedRef.current) {
      return;
    }

    saveTimeoutRef.current = setTimeout(async () => {
      await saveFormData(values, otherTxts);
    }, 600);
  }, [saveStatus]);

  // Save form data to backend
  const saveFormData = async (values: FormValues, otherTxts: Record<string, string>) => {
    // Skip if already saving to prevent concurrent saves
    if (saving) {
      return;
    }

    setSaveStatus('saving');
    setSaving(true);
    setSubmitError(null);

    try {
      // Collect profile fields to update
      const profileFields = [
        'full_name', 'date_of_birth', 'age_years', 'sex_at_birth', 'gender', 'city',
        'height_cm', 'weight_kg', 'waist_cm', 'activity_level',
        'smoking', 'alcohol', 'sleep_hours_avg', 'sleep_quality',
        'exercise_minutes_per_week', 'diet_pattern'
      ];

      const profileUpdate: Record<string, any> = {};
      for (const field of profileFields) {
        if (values[field]) {
          const answer = values[field];
          if (!answer.unknown && !answer.skipped && answer.value !== null && answer.value !== undefined) {
            profileUpdate[field] = answer.value;
          } else {
            profileUpdate[field] = null;
          }
        }
      }

      // Update profile fields
      if (Object.keys(profileUpdate).length > 0) {
        await updateProfile(profileUpdate);
      }

      // Collect and save answers (including "other" text answers)
      const answers: { question_id: string; answer_data: AnswerData }[] = [];
      for (const [questionId, answer] of Object.entries(values)) {
        if (!profileFields.includes(questionId) && !questionId.endsWith('_list')) {
          answers.push({ question_id: questionId, answer_data: answer });
        }
      }

      // Add "other" text answers
      for (const [fieldId, text] of Object.entries(otherTxts)) {
        if (text) {
          answers.push({
            question_id: `${fieldId}_other_text`,
            answer_data: { value: text, unknown: false, skipped: false }
          });
        }
      }

      if (answers.length > 0) {
        await upsertAnswers(answers);
      }

      // Save conditions (with "other" text)
      if (values['diagnosed_conditions']?.value) {
        const conditionCodes = values['diagnosed_conditions'].value as string[];
        const conditions = conditionCodes
          .filter(code => code !== 'none')
          .map(code => ({
            condition_code: code,
            condition_name: code === 'other' && otherTxts['diagnosed_conditions']
              ? otherTxts['diagnosed_conditions']
              : (CONDITION_LABELS[code] || code)
          }));
        await setConditions(conditions);
      }

      // Save symptoms (with "other" text)
      if (values['recurring_symptoms']?.value) {
        const symptomCodes = values['recurring_symptoms'].value as string[];
        const symptoms = symptomCodes
          .filter(code => code !== 'none')
          .map(code => ({
            symptom_code: code,
            notes: code === 'other' && otherTxts['recurring_symptoms']
              ? otherTxts['recurring_symptoms']
              : undefined
          }));
        await setSymptoms(symptoms);
      }

      // Save medications
      if (values['medications_list']?.value) {
        const meds = values['medications_list'].value as any[];
        await setMedications(meds.filter(m => m.name));
      }

      // Save supplements
      if (values['supplements_list']?.value) {
        const supps = values['supplements_list'].value as any[];
        await setSupplements(supps.filter(s => s.name));
      }

      // Save allergies
      if (values['allergies_list']?.value) {
        const allergies = values['allergies_list'].value as any[];
        await setAllergies(allergies.filter(a => a.allergen));
      }

      // Save family history
      if (values['family_history_list']?.value) {
        const history = values['family_history_list'].value as any[];
        await setFamilyHistory(history.filter(h => h.relative_type && h.condition_code));
      }

      lastSavedRef.current = JSON.stringify({ values, otherTxts });
      setSaveStatus('saved');

      // Reset save status after 2 seconds
      setTimeout(() => setSaveStatus('idle'), 2000);

    } catch (error: any) {
      console.error('Error saving form:', error);
      setSaveStatus('error');
      // Show error message to user
      const errorMsg = error?.message || 'Failed to save. Please try again.';
      setSubmitError(errorMsg);

      // Clear error after 5 seconds
      setTimeout(() => {
        setSaveStatus('idle');
        setSubmitError(null);
      }, 5000);
    } finally {
      setSaving(false);
    }
  };

  // Handle field change
  const handleFieldChange = useCallback((questionId: string, value: any) => {
    setFormValues(prev => {
      const newValues = {
        ...prev,
        [questionId]: {
          value: value,
          unknown: false,
          skipped: false,
        }
      };
      debouncedSave(newValues, otherTexts);
      return newValues;
    });

    // Clear validation error for this field
    if (validationErrors[questionId]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[questionId];
        return newErrors;
      });
    }
  }, [debouncedSave, otherTexts, validationErrors]);

  // Handle "other" text change
  const handleOtherTextChange = useCallback((fieldId: string, text: string) => {
    setOtherTexts(prev => {
      const newTexts = { ...prev, [fieldId]: text };
      debouncedSave(formValues, newTexts);
      return newTexts;
    });
  }, [debouncedSave, formValues]);

  // Navigate steps
  const handleNext = async () => {
    // Validate current step
    setShowErrors(true);
    setSubmitError(null);
    const isValid = validateCurrentStep();

    if (!isValid) {
      // Scroll to first error
      const firstErrorField = document.querySelector('.wizard-field.has-error');
      if (firstErrorField) {
        firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    // Save current step
    setSaving(true);
    try {
      await saveFormData(formValues, otherTexts);

      if (currentStep < PROFILE_FORM_SCHEMA.length - 1) {
        const nextStep = currentStep + 1;
        setCurrentStep(nextStep);
        setShowErrors(false);
        setValidationErrors({});
        await updateWizardState(nextStep + 1);
        // Scroll to top of content
        const wizardContent = document.querySelector('.wizard-content');
        if (wizardContent) {
          wizardContent.scrollTop = 0;
        }
      } else {
        // Complete wizard - mark as complete and show success screen
        await updateWizardState(PROFILE_FORM_SCHEMA.length, true);
        setShowSuccess(true);
      }
    } catch (error: any) {
      console.error('Error saving profile:', error);
      setSaveStatus('error');
      setSubmitError(error?.message || 'Failed to save profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      setShowErrors(false);
      setValidationErrors({});
      // Scroll to top of content
      const wizardContent = document.querySelector('.wizard-content');
      if (wizardContent) {
        wizardContent.scrollTop = 0;
      }
    }
  };

  const handleSaveAndExit = async () => {
    await saveFormData(formValues, otherTexts);
    await updateWizardState(currentStep + 1);
    navigate('/reports');
  };

  // Check if field should be shown
  const shouldShowField = (field: FormField): boolean => {
    if (!field.showIf) return true;

    const dependencyValue = formValues[field.showIf.questionId];
    if (!dependencyValue) return false;

    // Handle array values (multiselect)
    if (Array.isArray(dependencyValue.value)) {
      return field.showIf.values.some(v => dependencyValue.value.includes(v));
    }

    return field.showIf.values.includes(dependencyValue.value);
  };

  // Render individual field
  const renderField = (field: FormField) => {
    if (!shouldShowField(field)) return null;

    const value = formValues[field.questionId];
    const currentValue = value?.value;
    const hasError = showErrors && validationErrors[field.questionId];
    const isRequired = field.required || REQUIRED_FIELDS.includes(field.questionId);

    return (
      <div
        className={`wizard-field ${field.gridColumn === 'half' ? 'wizard-field-half' : 'wizard-field-full'} ${hasError ? 'has-error' : ''}`}
      >
        <div className="wizard-field-header">
          <label className="wizard-field-label">
            {field.label}
            {isRequired && <span className="required-mark">*</span>}
          </label>
        </div>

        {field.helpText && (
          <p className="wizard-field-help">{field.helpText}</p>
        )}

        <div className="wizard-field-input">
          {renderFieldInput(field, currentValue)}
        </div>

        {hasError && (
          <div className="wizard-field-error">
            <AlertCircle size={14} />
            <span>{validationErrors[field.questionId]}</span>
          </div>
        )}
      </div>
    );
  };

  // Render field input based on type
  const renderFieldInput = (field: FormField, currentValue: any) => {
    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            className="wizard-input"
            value={currentValue || ''}
            onChange={(e) => handleFieldChange(field.questionId, e.target.value)}
            placeholder={field.placeholder}
          />
        );

      case 'number':
        return (
          <div className="wizard-input-with-unit">
            <input
              type="number"
              className="wizard-input"
              value={currentValue ?? ''}
              onChange={(e) => handleFieldChange(field.questionId, e.target.value ? Number(e.target.value) : null)}
              placeholder={field.placeholder}
              min={field.min}
              max={field.max}
            />
            {field.unit && <span className="wizard-input-unit">{field.unit}</span>}
          </div>
        );

      case 'date':
        return (
          <input
            type="date"
            className="wizard-input"
            value={currentValue ? currentValue.split('T')[0] : ''}
            onChange={(e) => handleFieldChange(field.questionId, e.target.value)}
          />
        );

      case 'select':
        return (
          <select
            className="wizard-select"
            value={currentValue || ''}
            onChange={(e) => handleFieldChange(field.questionId, e.target.value)}
          >
            <option value="">Select...</option>
            {field.options?.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        );

      case 'radio':
        return (
          <div className="wizard-radio-group">
            {field.options?.map(opt => (
              <label key={opt.value} className={`wizard-radio ${currentValue === opt.value ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name={field.questionId}
                  value={opt.value}
                  checked={currentValue === opt.value}
                  onChange={(e) => handleFieldChange(field.questionId, e.target.value)}
                />
                <span className="radio-indicator"></span>
                <span className="radio-label">{opt.label}</span>
              </label>
            ))}
          </div>
        );

      case 'multiselect':
        return renderMultiselectField(field, currentValue);

      case 'textarea':
        return (
          <textarea
            className="wizard-textarea"
            value={currentValue || ''}
            onChange={(e) => handleFieldChange(field.questionId, e.target.value)}
            placeholder={field.placeholder}
            rows={3}
          />
        );

      case 'list':
        return renderListField(field, currentValue);

      default:
        return null;
    }
  };

  // Render multiselect with "Other" option
  const renderMultiselectField = (field: FormField, currentValue: any) => {
    const selectedValues = Array.isArray(currentValue) ? currentValue : [];
    const hasOtherOption = FIELDS_WITH_OTHER.includes(field.questionId);
    const showOtherInput = hasOtherOption && selectedValues.includes('other');

    // Add "Other" option if not present
    const options = [...(field.options || [])];
    if (hasOtherOption && !options.find(o => o.value === 'other')) {
      options.push({ value: 'other', label: 'Other (specify)' });
    }

    return (
      <div className="wizard-multiselect-container">
        <div className="wizard-multiselect">
          {options.map(opt => (
            <label
              key={opt.value}
              className={`wizard-checkbox ${selectedValues.includes(opt.value) ? 'selected' : ''}`}
            >
              <input
                type="checkbox"
                checked={selectedValues.includes(opt.value)}
                onChange={(e) => {
                  let newValue: string[];
                  if (opt.value === 'none') {
                    newValue = e.target.checked ? ['none'] : [];
                  } else {
                    newValue = selectedValues.filter(v => v !== 'none');
                    if (e.target.checked) {
                      newValue = [...newValue, opt.value];
                    } else {
                      newValue = newValue.filter(v => v !== opt.value);
                      // Clear "other" text if unchecking "other"
                      if (opt.value === 'other') {
                        setOtherTexts(prev => ({ ...prev, [field.questionId]: '' }));
                      }
                    }
                  }
                  handleFieldChange(field.questionId, newValue);
                }}
              />
              <span className="checkbox-indicator">
                <Check size={12} />
              </span>
              <span className="checkbox-label">{opt.label}</span>
            </label>
          ))}
        </div>

        {/* "Other" text input */}
        {showOtherInput && (
          <div className="wizard-other-input">
            <input
              type="text"
              className="wizard-input"
              placeholder="Please specify..."
              value={otherTexts[field.questionId] || ''}
              onChange={(e) => handleOtherTextChange(field.questionId, e.target.value)}
            />
          </div>
        )}
      </div>
    );
  };

  // Render list field (for medications, allergies, etc.)
  const renderListField = (field: FormField, currentValue: any) => {
    const items = Array.isArray(currentValue) ? currentValue : [];

    const addItem = () => {
      const newItem: Record<string, string> = {};
      field.listConfig?.fields.forEach(f => {
        newItem[f.name] = '';
      });
      handleFieldChange(field.questionId, [...items, newItem]);
    };

    const updateItem = (index: number, fieldName: string, value: string) => {
      const newItems = [...items];
      newItems[index] = { ...newItems[index], [fieldName]: value };
      handleFieldChange(field.questionId, newItems);
    };

    const removeItem = (index: number) => {
      const newItems = items.filter((_: any, i: number) => i !== index);
      handleFieldChange(field.questionId, newItems);
    };

    return (
      <div className="wizard-list">
        {items.map((item: any, index: number) => (
          <div key={index} className="wizard-list-item">
            <div className="wizard-list-item-fields">
              {field.listConfig?.fields.map(f => (
                <div key={f.name} className="wizard-list-field">
                  <label className="wizard-list-field-label">{f.label}</label>
                  {f.type === 'select' ? (
                    <select
                      className="wizard-select"
                      value={item[f.name] || ''}
                      onChange={(e) => updateItem(index, f.name, e.target.value)}
                    >
                      <option value="">Select...</option>
                      {f.options?.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={f.type}
                      className="wizard-input wizard-input-sm"
                      value={item[f.name] || ''}
                      onChange={(e) => updateItem(index, f.name, e.target.value)}
                    />
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              className="wizard-list-remove"
              onClick={() => removeItem(index)}
            >
              <X size={16} />
            </button>
          </div>
        ))}

        <button type="button" className="wizard-list-add" onClick={addItem}>
          <Plus size={16} />
          <span>Add {field.label.replace(/s$/, '')}</span>
        </button>
      </div>
    );
  };

  // Current step data
  const currentStepData = PROFILE_FORM_SCHEMA[currentStep];

  // Loading state
  if (loading) {
    return (
      <div className="health-profile-page">
        <div className="wizard-loading">
          <Loader2 className="animate-spin" size={32} />
          <p>Loading your health profile...</p>
        </div>
      </div>
    );
  }

  // Welcome / Start Screen
  if (showWelcome) {
    return (
      <div className="health-profile-page">
        <div className="welcome-screen">
          <button className="welcome-back-btn" onClick={handleSaveAndExit}>
            <ArrowLeft size={18} />
            Back to Reports
          </button>

          <div className="welcome-content">
            <div className="welcome-icon">
              <Heart size={48} />
            </div>

            <h1 className="welcome-title">Complete Your Health Profile</h1>

            <div className="welcome-eta">
              <Clock size={18} />
              <span>Takes approximately 5-7 minutes</span>
            </div>

            <div className="welcome-benefits">
              <div className="benefit-item">
                <TrendingUp size={20} />
                <div>
                  <h3>Better Recommendations</h3>
                  <p>Get personalized health insights based on your profile</p>
                </div>
              </div>

              <div className="benefit-item">
                <Shield size={20} />
                <div>
                  <h3>Accurate Health Index</h3>
                  <p>Your health score will be more meaningful with complete data</p>
                </div>
              </div>

              <div className="benefit-item">
                <AlertCircle size={20} />
                <div>
                  <h3>Required Information</h3>
                  <p>Only a few fields are required - the rest are optional</p>
                </div>
              </div>
            </div>

            <div className="welcome-actions">
              <button
                className="wizard-btn wizard-btn-primary welcome-start-btn"
                onClick={() => setShowWelcome(false)}
              >
                Get Started
                <ChevronRight size={18} />
              </button>
            </div>

          </div>
        </div>
      </div>
    );
  }

  // Show success screen after completion
  if (showSuccess) {
    return (
      <ProfileSuccessScreen
        autoRedirect={true}
        redirectDelay={2000}
      />
    );
  }

  return (
    <div className="health-profile-page">
      <div className="health-profile-wizard">
        {/* Progress Header */}
        <div className="wizard-header">
          <button className="wizard-back-btn" onClick={handleSaveAndExit}>
            <ArrowLeft size={18} />
            Save & Exit
          </button>

          <div className="wizard-progress">
            <div className="wizard-progress-bar">
              <div
                className="wizard-progress-fill"
                style={{ width: `${((currentStep + 1) / PROFILE_FORM_SCHEMA.length) * 100}%` }}
              />
            </div>
            <div className="wizard-progress-text">
              Step {currentStep + 1} of {PROFILE_FORM_SCHEMA.length} • <strong>{completionPercent}%</strong> complete
            </div>
          </div>

          <div className="wizard-save-status">
            {saveStatus === 'saving' && (
              <span className="status-saving">
                <Loader2 className="animate-spin" size={14} />
                Saving...
              </span>
            )}
            {saveStatus === 'saved' && (
              <span className="status-saved">
                <Check size={14} />
                Saved
              </span>
            )}
            {saveStatus === 'error' && (
              <span className="status-error">
                <AlertCircle size={14} />
                Save failed
              </span>
            )}
          </div>
        </div>

        {/* Step Content */}
        <div className="wizard-content">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{
                duration: 0.5,
                ease: [0.4, 0.0, 0.2, 1]
              }}
              className="wizard-step"
            >
              <div className="wizard-step-header">
                <h2 className="wizard-step-title">{currentStepData.title}</h2>
                <p className="wizard-step-description">{currentStepData.description}</p>
              </div>

              <div className="wizard-fields-grid">
                {currentStepData.fields.map((field, index) => (
                  <motion.div
                    key={field.questionId}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.4,
                      delay: index * 0.1,
                      ease: [0.4, 0.0, 0.2, 1]
                    }}
                  >
                    {renderField(field)}
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Navigation Footer */}
        <div className="wizard-footer">
          <div className="wizard-footer-left">
            {currentStep > 0 && (
              <button
                className="wizard-btn wizard-btn-secondary"
                onClick={handlePrevious}
              >
                <ChevronLeft size={18} />
                Back
              </button>
            )}
          </div>

          <div className="wizard-footer-center">
            {submitError && (
              <div className="wizard-submit-error">
                <AlertCircle size={16} />
                <span>{submitError}</span>
              </div>
            )}
          </div>

          <div className="wizard-footer-right">
            <button
              className="wizard-btn wizard-btn-primary"
              onClick={handleNext}
              disabled={saving}
            >
              {saving ? (
                <Loader2 className="animate-spin" size={18} />
              ) : currentStep === PROFILE_FORM_SCHEMA.length - 1 ? (
                <>
                  Complete
                  <Check size={18} />
                </>
              ) : (
                <>
                  Next
                  <ChevronRight size={18} />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Completion indicator */}
        <div className="wizard-completion-indicator">
          <div className="completion-score">
            Profile: <strong>{completionPercent}%</strong> complete
          </div>
        </div>
      </div>
    </div>
  );
}
