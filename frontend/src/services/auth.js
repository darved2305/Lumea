import axios from 'axios'
import { API_BASE_URL } from '../config/api'
import { getTokenSync, removeToken } from './tokenService'

const API_URL = API_BASE_URL

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // Enable sending cookies
})

api.interceptors.request.use(config => {
  const token = getTokenSync()
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
  removeToken()
}
