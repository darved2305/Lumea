import { motion } from 'framer-motion'
import './Logo.css'
import logoImage from '../../assets/logo.png'

interface LogoProps {
  className?: string
  variant?: 'header' | 'footer' | 'dashboard'
}

function Logo({ className = '', variant = 'header' }: LogoProps) {
  return (
    <motion.div 
      className={`logo-component ${variant} ${className}`}
      whileHover={{ scale: 1.05 }}
      transition={{ type: 'spring', stiffness: 400 }}
    >
      <img src={logoImage} alt="Lumea" className="logo-image" />
    </motion.div>
  )
}

export default Logo
