import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // Enable sending cookies
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

interface SignupResponse {
  access_token: string
  user: {
    id: string
    email: string
    full_name: string
  }
}

interface LoginResponse {
  access_token: string
  user: {
    id: string
    email: string
    full_name: string
  }
}

interface MeResponse {
  id: string
  email: string
  full_name: string
}

export const signup = async (fullName: string, email: string, password: string): Promise<SignupResponse> => {
  const response = await api.post<SignupResponse>('/api/auth/register', {
    full_name: fullName,
    email,
    password
  })
  return response.data
}

export const login = async (email: string, password: string): Promise<LoginResponse> => {
  const response = await api.post<LoginResponse>('/api/auth/login', {
    email,
    password
  })
  return response.data
}

export const getMe = async (): Promise<MeResponse> => {
  const response = await api.get<MeResponse>('/api/me')
  return response.data
}

export const logout = async (): Promise<void> => {
  await api.post('/api/auth/logout')
  localStorage.removeItem('access_token')
}
