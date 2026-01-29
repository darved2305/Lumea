import { motion } from 'framer-motion'
import Button from '../ui/Button'
import Card from '../ui/Card'
import './SnapshotPanel.css'

interface PatientProfile {
  fullName?: string
  age?: number
  gender?: string
  heightCm?: number
  weightKg?: number
  bmi?: number
  conditions?: string[]
}

interface Reminder {
  title: string
  reason: string
  dueDate: string
  urgency: 'overdue' | 'soon' | 'ok'
  frequencyMonths: number
}

interface SnapshotPanelProps {
  profile: PatientProfile | null
  reminders: Reminder[]
  isGuest: boolean
  onEditProfile?: () => void
  onSaveProfile?: () => void
}

export default function SnapshotPanel({
  profile,
  reminders,
  isGuest,
  onEditProfile,
  onSaveProfile
}: SnapshotPanelProps) {
  const getBmiCategory = (bmi?: number) => {
    if (!bmi) return null
    if (bmi < 18.5) return { label: 'Underweight', color: '#f59e0b' }
    if (bmi < 25) return { label: 'Normal', color: '#4a7c59' }
    if (bmi < 30) return { label: 'Overweight', color: '#f59e0b' }
    return { label: 'Obese', color: '#d64545' }
  }

  const bmiCategory = getBmiCategory(profile?.bmi)

  const urgencyConfig = {
    overdue: { color: '#d64545', icon: '🔴', label: 'Overdue' },
    soon: { color: '#f59e0b', icon: '🟡', label: 'Due Soon' },
    ok: { color: '#4a7c59', icon: '🟢', label: 'Upcoming' }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))

    if (diffDays < 0) {
      return `${Math.abs(diffDays)} days overdue`
    } else if (diffDays === 0) {
      return 'Today'
    } else if (diffDays === 1) {
      return 'Tomorrow'
    } else if (diffDays <= 30) {
      return `In ${diffDays} days`
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    }
  }

  return (
    <div className="snapshot-panel">
      <motion.div
        className="snapshot-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h2 className="snapshot-title">Patient Snapshot</h2>
        {isGuest && onSaveProfile && (
          <Button variant="outline" size="sm" onClick={onSaveProfile}>
            💾 Save Profile
          </Button>
        )}
      </motion.div>

      {/* Profile Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card hover>
          <div className="profile-card">
            <div className="profile-header">
              <div className="profile-avatar">
                {profile?.gender === 'male' ? '👨' : profile?.gender === 'female' ? '👩' : '🧑'}
              </div>
              <div className="profile-info">
                <h3 className="profile-name">{profile?.fullName || 'Guest User'}</h3>
                <p className="profile-meta">
                  {profile?.age && `${profile.age} years`}
                  {profile?.age && profile?.gender && ' • '}
                  {profile?.gender && profile.gender.charAt(0).toUpperCase() + profile.gender.slice(1)}
                </p>
              </div>
            </div>

            <div className="profile-metrics">
              {profile?.heightCm && (
                <div className="metric">
                  <span className="metric-label">Height</span>
                  <span className="metric-value">{profile.heightCm} cm</span>
                </div>
              )}
              {profile?.weightKg && (
                <div className="metric">
                  <span className="metric-label">Weight</span>
                  <span className="metric-value">{profile.weightKg} kg</span>
                </div>
              )}
              {profile?.bmi && (
                <div className="metric">
                  <span className="metric-label">BMI</span>
                  <span className="metric-value" style={{ color: bmiCategory?.color }}>
                    {profile.bmi} <span className="metric-category">({bmiCategory?.label})</span>
                  </span>
                </div>
              )}
            </div>

            {profile?.conditions && profile.conditions.length > 0 && (
              <div className="profile-conditions">
                <span className="conditions-label">Health Conditions:</span>
                <div className="conditions-list">
                  {profile.conditions.map(condition => (
                    <span key={condition} className="condition-tag">{condition}</span>
                  ))}
                </div>
              </div>
            )}

            {onEditProfile && (
              <Button variant="secondary" size="sm" fullWidth onClick={onEditProfile}>
                Edit Profile
              </Button>
            )}
          </div>
        </Card>
      </motion.div>

      {/* Reminders Section */}
      <motion.div
        className="reminders-section"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <h3 className="reminders-title">Health Reminders</h3>

        {reminders.length === 0 ? (
          <Card>
            <div className="reminders-empty">
              <span className="reminders-empty-icon">📅</span>
              <p>No reminders yet. Complete your profile to get personalized health reminders.</p>
            </div>
          </Card>
        ) : (
          <div className="reminders-list">
            {reminders.map((reminder, index) => {
              const config = urgencyConfig[reminder.urgency]
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                >
                  <Card hover>
                    <div className="reminder-card">
                      <div className="reminder-header">
                        <span className="reminder-icon">{config.icon}</span>
                        <div className="reminder-title-section">
                          <h4 className="reminder-title">{reminder.title}</h4>
                          <span
                            className="reminder-urgency"
                            style={{ color: config.color }}
                          >
                            {config.label}
                          </span>
                        </div>
                      </div>
                      <p className="reminder-reason">{reminder.reason}</p>
                      <div className="reminder-footer">
                        <span className="reminder-date">{formatDate(reminder.dueDate)}</span>
                        <span className="reminder-frequency">
                          Every {reminder.frequencyMonths} months
                        </span>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )
            })}
          </div>
        )}
      </motion.div>
    </div>
  )
}
