import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import Logo from './ui/Logo'
import LanguageSwitcher from './LanguageSwitcher'
import './Header.css'

function Header() {
  const { t } = useTranslation()

  const navLinks = [
    { label: t('header.nav.features'), href: '#features' },
    { label: t('header.nav.howItWorks'), href: '#how-it-works' },
    { label: t('header.nav.privacySecurity'), href: '#privacy' },
    { label: t('header.nav.contact'), href: '#contact' },
  ]

  return (
    <motion.header 
      className="header"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
    >
      <div className="header-container">
        <Link to="/">
          <Logo variant="header" />
        </Link>

        <nav className="nav">
          <ul className="nav-list">
            {navLinks.map((link, index) => (
              <motion.li 
                key={link.label} 
                className="nav-item"
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 * index, duration: 0.5 }}
              >
                <motion.a 
                  href={link.href} 
                  className="nav-link"
                  whileHover={{ scale: 1.1, color: '#4a7c59' }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  {link.label}
                </motion.a>
              </motion.li>
            ))}
          </ul>
        </nav>

        <motion.div 
          className="header-actions"
          initial={{ x: 100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.6 }}
        >
          <LanguageSwitcher />
          <motion.div
            whileHover={{ scale: 1.08, boxShadow: '0 8px 25px rgba(74, 124, 89, 0.3)' }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 10 }}
          >
            <Link to="/login" className="book-session-btn">
              {t('header.cta')}
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </motion.header>
  )
}

export default Header
