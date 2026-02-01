/**
 * Health Profile Page
 * 
 * Full-page wizard for completing health profile.
 * Replaces the modal-based approach.
 * 
 * Features:
 * - Welcome screen with ETA
 * - Multi-step wizard with progress tracking
 * - Autosave with visual feedback
 * - "Other" option for multi-selects
 * - Proper completion percentage calculation
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronLeft, 
  ChevronRight, 
  Check, 
  HelpCircle, 
  SkipForward,
  Loader2,
  AlertCircle,
  CheckCircle2,
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
  CONDITION_LABELS 
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
  setGeneticTests,
  updateWizardState,
  AnswerData,
} from '../services/profileApi';
import './HealthProfile.css';

type FormValues = Record<string, AnswerData>;

// Fields that support "Other" option
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
  
  // "Other" text values for multi-selects
  const [otherTexts, setOtherTexts] = useState<Record<string, string>>({});
  
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
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
        
        // Load from answers
        for (const answer of data.answers) {
          values[answer.question_id] = answer.answer_data;
          
          // Check for "other" text answers
          if (answer.question_id.endsWith('_other_text')) {
            const baseField = answer.question_id.replace('_other_text', '');
            otherTxts[baseField] = answer.answer_data.value || '';
          }
        }
        
        // Load conditions as multiselect value
        if (data.conditions.length > 0) {
          const codes = data.conditions.map(c => c.condition_code);
          // Check if any are "other" type
          const hasOther = data.conditions.some(c => c.condition_code === 'other');
          const otherCondition = data.conditions.find(c => c.condition_code === 'other');
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
        
        // Load genetic tests
        if (data.genetic_tests.length > 0) {
          values['genetic_tests_any'] = { value: 'yes', unknown: false, skipped: false };
          values['genetic_tests_list'] = {
            value: data.genetic_tests.map(g => ({
              mutation_name: g.mutation_name,
              result: g.result || ''
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
    // Define weights: essential fields count more
    const ESSENTIAL_WEIGHT = 2;
    const NORMAL_WEIGHT = 1;
    
    let totalWeight = 0;
    let answeredWeight = 0;
    
    // Go through all fields in all steps
    for (const step of PROFILE_FORM_SCHEMA) {
      for (const field of step.fields) {
        // Skip conditional fields if their condition isn't met
        if (field.showIf) {
          const dependencyValue = formValues[field.showIf.questionId];
          if (!dependencyValue) continue;
          
          if (dependencyValue.unknown) {
            if (!field.showIf.values.includes('unknown')) continue;
          } else if (Array.isArray(dependencyValue.value)) {
            if (!field.showIf.values.some(v => dependencyValue.value.includes(v))) continue;
          } else {
            if (!field.showIf.values.includes(dependencyValue.value)) continue;
          }
        }
        
        const weight = field.essential ? ESSENTIAL_WEIGHT : NORMAL_WEIGHT;
        totalWeight += weight;
        
        // Check if field is answered
        const answer = formValues[field.questionId];
        if (answer) {
          // Unknown/skipped counts as "answered" (user intentionally responded)
          if (answer.unknown || answer.skipped) {
            answeredWeight += weight;
          } else if (answer.value !== null && answer.value !== undefined && answer.value !== '') {
            // Has actual value
            if (Array.isArray(answer.value)) {
              if (answer.value.length > 0) {
                answeredWeight += weight;
              }
            } else {
              answeredWeight += weight;
            }
          }
        }
      }
    }
    
    if (totalWeight === 0) return 0;
    return Math.round((answeredWeight / totalWeight) * 100);
  }, [formValues]);
  
  // Debounced autosave
  const debouncedSave = useCallback((values: FormValues, otherTxts: Record<string, string>) => {
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
  }, []);
  
  // Save form data to backend
  const saveFormData = async (values: FormValues, otherTxts: Record<string, string>) => {
    setSaveStatus('saving');
    setSaving(true);
    
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
      
      // Save genetic tests
      if (values['genetic_tests_list']?.value) {
        const tests = values['genetic_tests_list'].value as any[];
        await setGeneticTests(tests.filter(t => t.mutation_name));
      }
      
      lastSavedRef.current = JSON.stringify({ values, otherTxts });
      setSaveStatus('saved');
      
      // Reset save status after 2 seconds
      setTimeout(() => setSaveStatus('idle'), 2000);
      
    } catch (error) {
      console.error('Error saving form:', error);
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };
  
  // Handle field change
  const handleFieldChange = useCallback((questionId: string, value: any, flags?: { unknown?: boolean; skipped?: boolean }) => {
    setFormValues(prev => {
      const newValues = {
        ...prev,
        [questionId]: {
          value: flags?.unknown || flags?.skipped ? null : value,
          unknown: flags?.unknown || false,
          skipped: flags?.skipped || false,
        }
      };
      debouncedSave(newValues, otherTexts);
      return newValues;
    });
  }, [debouncedSave, otherTexts]);
  
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
    // Save current step
    await saveFormData(formValues, otherTexts);
    
    if (currentStep < PROFILE_FORM_SCHEMA.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      await updateWizardState(nextStep + 1);
    } else {
      // Complete wizard - save and navigate back
      await updateWizardState(PROFILE_FORM_SCHEMA.length, true);
      navigate('/reports');
    }
  };
  
  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };
  
  const handleSaveAndExit = async () => {
    await saveFormData(formValues, otherTexts);
    await updateWizardState(currentStep + 1);
    navigate('/reports');
  };
  
  const handleSkip = () => {
    navigate('/reports');
  };
  
  // Check if field should be shown
  const shouldShowField = (field: FormField): boolean => {
    if (!field.showIf) return true;
    
    const dependencyValue = formValues[field.showIf.questionId];
    if (!dependencyValue) return false;
    
    // Handle unknown flag
    if (dependencyValue.unknown) {
      return field.showIf.values.includes('unknown');
    }
    
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
    const isUnknown = value?.unknown || false;
    const isSkipped = value?.skipped || false;
    const currentValue = value?.value;
    
    return (
      <motion.div 
        key={field.questionId}
        className="wizard-field"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
      >
        <div className="wizard-field-header">
          <label className="wizard-field-label">
            {field.label}
            {field.required && <span className="required-mark">*</span>}
            {field.essential && <span className="essential-badge">Important</span>}
          </label>
          
          <div className="wizard-field-toggles">
            {field.supportsUnknown && (
              <button
                type="button"
                className={`toggle-btn ${isUnknown ? 'active' : ''}`}
                onClick={() => handleFieldChange(field.questionId, null, { unknown: !isUnknown })}
                title="I don't know"
              >
                <HelpCircle size={14} />
                <span>Don't know</span>
              </button>
            )}
            {field.supportsSkip && (
              <button
                type="button"
                className={`toggle-btn ${isSkipped ? 'active' : ''}`}
                onClick={() => handleFieldChange(field.questionId, null, { skipped: !isSkipped })}
                title="Skip this question"
              >
                <SkipForward size={14} />
                <span>Skip</span>
              </button>
            )}
          </div>
        </div>
        
        {field.helpText && (
          <p className="wizard-field-help">{field.helpText}</p>
        )}
        
        {!isUnknown && !isSkipped && (
          <div className="wizard-field-input">
            {renderFieldInput(field, currentValue)}
          </div>
        )}
        
        {(isUnknown || isSkipped) && (
          <div className="wizard-field-skipped">
            {isUnknown ? "Marked as unknown" : "Skipped"}
          </div>
        )}
      </motion.div>
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
          <button className="welcome-back-btn" onClick={handleSkip}>
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
                <CheckCircle2 size={20} />
                <div>
                  <h3>Track Trends Over Time</h3>
                  <p>Compare lab results against your baseline</p>
                </div>
              </div>
            </div>
            
            <div className="welcome-note">
              <HelpCircle size={16} />
              <span>You can skip any question you don't know or prefer not to answer</span>
            </div>
            
            <div className="welcome-actions">
              <button 
                className="wizard-btn wizard-btn-primary welcome-start-btn"
                onClick={() => setShowWelcome(false)}
              >
                Start
                <ChevronRight size={18} />
              </button>
              
              <button 
                className="wizard-btn wizard-btn-ghost"
                onClick={handleSkip}
              >
                Skip for now
              </button>
            </div>
          </div>
        </div>
      </div>
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
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="wizard-step"
            >
              <h2 className="wizard-step-title">{currentStepData.title}</h2>
              <p className="wizard-step-description">{currentStepData.description}</p>
              
              <div className="wizard-fields">
                {currentStepData.fields.map(field => renderField(field))}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
        
        {/* Navigation Footer */}
        <div className="wizard-footer">
          <div className="wizard-footer-left">
            {currentStep > 0 ? (
              <button 
                className="wizard-btn wizard-btn-secondary"
                onClick={handlePrevious}
              >
                <ChevronLeft size={18} />
                Back
              </button>
            ) : (
              <button 
                className="wizard-btn wizard-btn-ghost"
                onClick={handleSkip}
              >
                Skip for now
              </button>
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
