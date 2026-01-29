import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Card from '../ui/Card'
import './GuestIntakeForm.css'

interface GuestProfile {
  fullName: string
  age: number
  gender: string
  heightCm: number
  weightKg: number
  conditions: string[]
  lastBloodTestAt?: string
  lastDentalAt?: string
  lastEyeExamAt?: string
}

interface GuestIntakeFormProps {
  onComplete: (profile: GuestProfile) => void
}

const conditionOptions = [
  'Diabetes',
  'Hypertension',
  'Thyroid',
  'Asthma',
  'None',
  'Other'
]

export default function GuestIntakeForm({ onComplete }: GuestIntakeFormProps) {
  const [formData, setFormData] = useState({
    fullName: '',
    age: '',
    gender: 'male',
    heightCm: '',
    weightKg: '',
    conditions: [] as string[],
    lastBloodTestAt: '',
    lastDentalAt: '',
    lastEyeExamAt: ''
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleConditionToggle = (condition: string) => {
    setFormData(prev => {
      const newConditions = prev.conditions.includes(condition)
        ? prev.conditions.filter(c => c !== condition)
        : [...prev.conditions, condition]
      return { ...prev, conditions: newConditions }
    })
  }

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (formData.age && (Number(formData.age) < 0 || Number(formData.age) > 150)) {
      newErrors.age = 'Age must be between 0 and 150'
    }
    if (formData.heightCm && (Number(formData.heightCm) <= 0 || Number(formData.heightCm) > 300)) {
      newErrors.heightCm = 'Height must be between 0 and 300 cm'
    }
    if (formData.weightKg && (Number(formData.weightKg) <= 0 || Number(formData.weightKg) > 500)) {
      newErrors.weightKg = 'Weight must be between 0 and 500 kg'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) {
      return
    }

    const profile: GuestProfile = {
      fullName: formData.fullName || 'Guest',
      age: Number(formData.age) || 30,
      gender: formData.gender,
      heightCm: Number(formData.heightCm) || 170,
      weightKg: Number(formData.weightKg) || 70,
      conditions: formData.conditions,
      lastBloodTestAt: formData.lastBloodTestAt || undefined,
      lastDentalAt: formData.lastDentalAt || undefined,
      lastEyeExamAt: formData.lastEyeExamAt || undefined
    }

    // Store in localStorage
    localStorage.setItem('guest_profile_v1', JSON.stringify(profile))
    onComplete(profile)
  }

  const bmi = formData.heightCm && formData.weightKg
    ? (Number(formData.weightKg) / Math.pow(Number(formData.heightCm) / 100, 2)).toFixed(1)
    : null

  return (
    <div className="guest-intake-container">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <Card>
          <div className="guest-intake-header">
            <h2 className="guest-intake-title">Quick Health Profile</h2>
            <p className="guest-intake-subtitle">
              Help us personalize your health reminders and insights
            </p>
          </div>

          <form onSubmit={handleSubmit} className="guest-intake-form">
            <div className="form-section">
              <h3 className="form-section-title">Basic Information</h3>
              <div className="form-row">
                <Input
                  label="Full Name"
                  placeholder="John Doe"
                  value={formData.fullName}
                  onChange={e => setFormData(prev => ({ ...prev, fullName: e.target.value }))}
                />
              </div>

              <div className="form-row form-row-2">
                <Input
                  type="number"
                  label="Age"
                  placeholder="30"
                  value={formData.age}
                  onChange={e => setFormData(prev => ({ ...prev, age: e.target.value }))}
                  error={errors.age}
                />

                <div className="input-wrapper">
                  <label className="input-label">Gender</label>
                  <select
                    className="input"
                    value={formData.gender}
                    onChange={e => setFormData(prev => ({ ...prev, gender: e.target.value }))}
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="form-section">
              <h3 className="form-section-title">Body Metrics</h3>
              <div className="form-row form-row-2">
                <Input
                  type="number"
                  label="Height (cm)"
                  placeholder="170"
                  value={formData.heightCm}
                  onChange={e => setFormData(prev => ({ ...prev, heightCm: e.target.value }))}
                  error={errors.heightCm}
                />

                <Input
                  type="number"
                  label="Weight (kg)"
                  placeholder="70"
                  value={formData.weightKg}
                  onChange={e => setFormData(prev => ({ ...prev, weightKg: e.target.value }))}
                  error={errors.weightKg}
                />
              </div>

              <AnimatePresence>
                {bmi && (
                  <motion.div
                    className="bmi-display"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <span className="bmi-label">BMI:</span>
                    <span className="bmi-value">{bmi}</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="form-section">
              <h3 className="form-section-title">Health Conditions</h3>
              <div className="conditions-grid">
                {conditionOptions.map(condition => (
                  <motion.button
                    key={condition}
                    type="button"
                    className={`condition-chip ${formData.conditions.includes(condition) ? 'condition-chip-active' : ''}`}
                    onClick={() => handleConditionToggle(condition)}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {condition}
                  </motion.button>
                ))}
              </div>
            </div>

            <div className="form-section">
              <h3 className="form-section-title">Last Checkup Dates (Optional)</h3>
              <div className="form-row form-row-3">
                <Input
                  type="date"
                  label="Blood Test"
                  value={formData.lastBloodTestAt}
                  onChange={e => setFormData(prev => ({ ...prev, lastBloodTestAt: e.target.value }))}
                />

                <Input
                  type="date"
                  label="Dental Checkup"
                  value={formData.lastDentalAt}
                  onChange={e => setFormData(prev => ({ ...prev, lastDentalAt: e.target.value }))}
                />

                <Input
                  type="date"
                  label="Eye Exam"
                  value={formData.lastEyeExamAt}
                  onChange={e => setFormData(prev => ({ ...prev, lastEyeExamAt: e.target.value }))}
                />
              </div>
            </div>

            <div className="form-actions">
              <Button type="submit" variant="primary" size="lg" fullWidth>
                Continue to Health Chat
              </Button>
            </div>
          </form>

          <p className="guest-intake-footer">
            🔒 Your data is stored locally. Register to sync across devices.
          </p>
        </Card>
      </motion.div>
    </div>
  )
}
