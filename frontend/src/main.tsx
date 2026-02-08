import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import './i18n/config'
import { initCapacitor } from './services/capacitorInit'

// Initialize Capacitor plugins (back button, network, splash screen, etc.)
initCapacitor().catch(err => console.warn('[Capacitor] Init warning:', err))

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
