import { useState, ChangeEvent, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthShell from '../components/AuthShell'
import { login } from '../services/auth'
import { setAuthToken } from '../utils/auth'

function Login() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    setError('')
  }

  // Parse error response - handles both string and Pydantic v2 validation error format
  const parseErrorMessage = (err: unknown): string => {
    const axiosError = err as { response?: { data?: { detail?: string | Array<{ msg?: string; loc?: string[] }> } } }
    const detail = axiosError.response?.data?.detail

    if (!detail) return 'Login failed. Please check your credentials.'
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map(e => e.msg || 'Validation error').join('. ') || 'Validation failed.'
    }
    return 'Login failed. Please check your credentials.'
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await login(formData.email, formData.password)
      await setAuthToken(data.access_token)
      navigate('/dashboard')
    } catch (err: unknown) {
      setError(parseErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Welcome Back"
      subtitle="Sign in to continue your health journey"
      footerText="Don't have an account?"
      footerLink="/signup"
      footerLinkText="Sign up"
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="email" className="form-label">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            value={formData.email}
            onChange={handleChange}
            className="form-input"
            placeholder="you@example.com"
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="password" className="form-label">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            value={formData.password}
            onChange={handleChange}
            className="form-input"
            placeholder="Enter your password"
            disabled={loading}
          />
        </div>

        {error && <div className="form-error">{error}</div>}

        <button type="submit" className="auth-button" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </AuthShell>
  )
}

export default Login
