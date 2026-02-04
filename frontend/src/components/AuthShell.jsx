import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import Logo from './ui/Logo'
import './AuthShell.css'

function AuthShell({ children, title, subtitle, footerText, footerLink, footerLinkText }) {
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
            <Logo variant="header" />
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
