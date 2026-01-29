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

export const signup = async (fullName, email, password) => {
  const response = await api.post('/api/auth/register', {
    full_name: fullName,
    email,
    password
  })
  return response.data
}

export const login = async (email, password) => {
  const response = await api.post('/api/auth/login', {
    email,
    password
  })
  return response.data
}

export const getMe = async () => {
  const response = await api.get('/api/me')
  return response.data
}

export const logout = async () => {
  await api.post('/api/auth/logout')
  localStorage.removeItem('access_token')
}

