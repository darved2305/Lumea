import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import GuestIntakeForm from '../components/health-chat/GuestIntakeForm'
import ChatPanel from '../components/health-chat/ChatPanel'
import SnapshotPanel from '../components/health-chat/SnapshotPanel'
import Header from '../components/Header'
import './HealthChat.css'

interface User {
  id: string
  email: string
  fullName: string
}

interface PatientProfile {
  id?: string
  userId?: string
  fullName?: string
  age?: number
  gender?: string
  heightCm?: number
  weightKg?: number
  bmi?: number
  conditions?: string[]
  lastBloodTestAt?: string
  lastDentalAt?: string
  lastEyeExamAt?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
}

interface Reminder {
  title: string
  reason: string
  dueDate: string
  urgency: 'overdue' | 'soon' | 'ok'
  frequencyMonths: number
}

const API_BASE = 'http://localhost:8000'

export default function HealthChat() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(true)
  const [, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<PatientProfile | null>(null)
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [showIntake, setShowIntake] = useState(false)
  const [isGuest, setIsGuest] = useState(false)
  const [guestKey] = useState(() => {
    let key = localStorage.getItem('guest_key')
    if (!key) {
      key = `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('guest_key', key)
    }
    return key
  })
  const [isSendingMessage, setIsSendingMessage] = useState(false)

  // Check authentication and load data
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Try to get authenticated user
        const meResponse = await fetch(`${API_BASE}/api/me`, {
          credentials: 'include'
        })

        if (meResponse.ok) {
          const userData = await meResponse.json()
          setUser(userData)
          setIsGuest(false)

          // Fetch profile
          const profileResponse = await fetch(`${API_BASE}/api/profile`, {
            credentials: 'include'
          })

          if (profileResponse.ok) {
            const profileData = await profileResponse.json()
            setProfile(profileData)
          }

          // Fetch reminders
          const remindersResponse = await fetch(`${API_BASE}/api/reminders`, {
            credentials: 'include'
          })

          if (remindersResponse.ok) {
            const remindersData = await remindersResponse.json()
            setReminders(remindersData.reminders || [])
          }

          // Fetch chat history
          const historyResponse = await fetch(`${API_BASE}/api/chat/history`, {
            credentials: 'include'
          })

          if (historyResponse.ok) {
            const historyData = await historyResponse.json()
            setMessages(historyData.messages || [])
          }
        } else {
          // Not authenticated - check for guest profile
          const guestProfile = localStorage.getItem('guest_profile_v1')
          if (guestProfile) {
            const parsedProfile = JSON.parse(guestProfile)
            setProfile(parsedProfile)
            setIsGuest(true)
            
            // Compute guest reminders locally
            const guestReminders = computeGuestReminders(parsedProfile)
            setReminders(guestReminders)
          } else {
            // Show intake form
            setShowIntake(true)
            setIsGuest(true)
          }
        }
      } catch (error) {
        console.error('Error initializing app:', error)
        // Check for guest profile
        const guestProfile = localStorage.getItem('guest_profile_v1')
        if (guestProfile) {
          const parsedProfile = JSON.parse(guestProfile)
          setProfile(parsedProfile)
          setIsGuest(true)
          const guestReminders = computeGuestReminders(parsedProfile)
          setReminders(guestReminders)
        } else {
          setShowIntake(true)
          setIsGuest(true)
        }
      } finally {
        setIsLoading(false)
      }
    }

    initializeApp()
  }, [])

  const computeGuestReminders = (profile: PatientProfile): Reminder[] => {
    const reminders: Reminder[] = []
    const today = new Date()

    const getUrgency = (dueDate: Date): 'overdue' | 'soon' | 'ok' => {
      const days = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
      if (days < 0) return 'overdue'
      if (days <= 30) return 'soon'
      return 'ok'
    }

    // Dental checkup - every 6 months
    if (profile.lastDentalAt) {
      const lastDental = new Date(profile.lastDentalAt)
      const nextDental = new Date(lastDental)
      nextDental.setMonth(nextDental.getMonth() + 6)
      reminders.push({
        title: 'Dental Checkup',
        reason: 'Regular dental hygiene and oral health maintenance',
        dueDate: nextDental.toISOString(),
        urgency: getUrgency(nextDental),
        frequencyMonths: 6
      })
    } else {
      reminders.push({
        title: 'Dental Checkup',
        reason: 'Schedule your routine dental checkup',
        dueDate: today.toISOString(),
        urgency: 'overdue',
        frequencyMonths: 6
      })
    }

    // Basic blood work - every 12 months
    if (profile.lastBloodTestAt) {
      const lastBlood = new Date(profile.lastBloodTestAt)
      const nextBlood = new Date(lastBlood)
      nextBlood.setMonth(nextBlood.getMonth() + 12)
      reminders.push({
        title: 'Basic Blood Work',
        reason: 'Annual health screening and wellness check',
        dueDate: nextBlood.toISOString(),
        urgency: getUrgency(nextBlood),
        frequencyMonths: 12
      })
    } else {
      reminders.push({
        title: 'Basic Blood Work',
        reason: 'Recommended to schedule your health screening',
        dueDate: today.toISOString(),
        urgency: 'overdue',
        frequencyMonths: 12
      })
    }

    // Eye exam - yearly
    if (profile.lastEyeExamAt) {
      const lastEye = new Date(profile.lastEyeExamAt)
      const nextEye = new Date(lastEye)
      nextEye.setMonth(nextEye.getMonth() + 12)
      reminders.push({
        title: 'Eye Examination',
        reason: 'Annual eye health check',
        dueDate: nextEye.toISOString(),
        urgency: getUrgency(nextEye),
        frequencyMonths: 12
      })
    } else {
      reminders.push({
        title: 'Eye Examination',
        reason: 'Recommended to schedule your eye health check',
        dueDate: today.toISOString(),
        urgency: 'overdue',
        frequencyMonths: 12
      })
    }

    // Sort by urgency
    const urgencyOrder = { overdue: 0, soon: 1, ok: 2 }
    reminders.sort((a, b) => urgencyOrder[a.urgency] - urgencyOrder[b.urgency])

    return reminders
  }

  const handleIntakeComplete = (guestProfile: any) => {
    setProfile(guestProfile)
    setShowIntake(false)
    const guestReminders = computeGuestReminders(guestProfile)
    setReminders(guestReminders)
  }

  const handleSendMessage = async (message: string) => {
    // Add user message immediately
    const userMessage: Message = {
      id: `temp_${Date.now()}`,
      role: 'user',
      content: message,
      createdAt: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsSendingMessage(true)

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          message,
          guest_key: isGuest ? guestKey : undefined
        })
      })

      if (response.ok) {
        const assistantMessage = await response.json()
        setMessages(prev => [...prev, assistantMessage])
      } else {
        // Fallback response
        const fallbackMessage: Message = {
          id: `fallback_${Date.now()}`,
          role: 'assistant',
          content: "I'm here to help! However, I'm having trouble connecting right now. Please try again in a moment.",
          createdAt: new Date().toISOString()
        }
        setMessages(prev => [...prev, fallbackMessage])
      }
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: "I'm having trouble connecting. Please check your internet connection and try again.",
        createdAt: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsSendingMessage(false)
    }
  }

  const handleSaveProfile = () => {
    navigate('/signup')
  }

  if (isLoading) {
    return (
      <div className="health-chat-loading">
        <motion.div
          className="loading-spinner"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        >
          ⚕️
        </motion.div>
        <p>Loading your health companion...</p>
      </div>
    )
  }

  if (showIntake) {
    return <GuestIntakeForm onComplete={handleIntakeComplete} />
  }

  return (
    <div className="health-chat-page">
      <Header />
      
      <motion.div
        className="health-chat-container"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        <div className="health-chat-layout">
          <div className="chat-section">
            <ChatPanel
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isSendingMessage}
            />
          </div>

          <div className="snapshot-section">
            <SnapshotPanel
              profile={profile}
              reminders={reminders}
              isGuest={isGuest}
              onSaveProfile={isGuest ? handleSaveProfile : undefined}
            />
          </div>
        </div>
      </motion.div>
    </div>
  )
}
