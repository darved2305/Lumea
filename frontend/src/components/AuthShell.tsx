import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { ReactNode } from 'react'
import './AuthShell.css'


interface AuthShellProps {
  children: ReactNode
  title: string
  subtitle: string
  footerText: string
  footerLink: string
  footerLinkText: string
}

function AuthShell({ children, title, subtitle, footerText, footerLink, footerLinkText }: AuthShellProps) {
  return (
    <div className="auth-shell">
      <div className="auth-container">
        <motion.div
          className="auth-header"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Link to="/" className="auth-logo">
            <span className="logo-main">Co-Code</span>
            <span className="logo-sub">GGW</span>
          </Link>
        </motion.div>

        <motion.div
          className="auth-card"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <h1 className="auth-title">{title}</h1>
          <p className="auth-subtitle">{subtitle}</p>
          
          {children}

          <div className="auth-footer">
            <p>
              {footerText}{' '}
              <Link to={footerLink} className="auth-link">
                {footerLinkText}
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default AuthShell
